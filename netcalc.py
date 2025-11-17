# netcalc.py
from ipaddress import ip_address, ip_network, IPv4Address, IPv4Network

class NetcalcError(ValueError):
    """Exception spécifique aux validations/calculs réseau."""
    pass

# Contraintes projet
VALID_PREFIX_MIN = 8
VALID_PREFIX_MAX = 30

# Table des masques pointés contigus -> /prefix (pré-calculée)
MASK_TO_PREFIX = {str(ip_network(f"0.0.0.0/{p}").netmask): p for p in range(33)}


def _validate_prefix_range(prefix: int):
    """Vérifie que le préfixe est dans la plage autorisée /8.. /30."""
    if not (VALID_PREFIX_MIN <= prefix <= VALID_PREFIX_MAX):
        raise NetcalcError(
            f"Masque hors limites: /{prefix}. Autorisés: /{VALID_PREFIX_MIN} à /{VALID_PREFIX_MAX}."
        )


def _prefix_to_mask(prefix: int) -> str:
    """Retourne le masque décimal pointé correspondant au /prefix."""
    return str(ip_network(f"0.0.0.0/{prefix}").netmask)


def _default_classful_prefix_and_guard(ip_str: str) -> int:
    """
    En mode classful, n'autoriser que les classes A/B/C et renvoyer
    le préfixe par défaut de la classe:
      - A: /8  (1..126)
      - B: /16 (128..191)
      - C: /24 (192..223)
    Refuse 0.x, 127.x, 224+ (D/E).
    """
    first = int(ip_str.split('.')[0])
    if 1 <= first <= 126:     # Classe A (exclut 0 et 127)
        return 8
    elif 128 <= first <= 191: # Classe B
        return 16
    elif 192 <= first <= 223: # Classe C
        return 24
    else:
        raise NetcalcError("Mode classful: classes A/B/C uniquement (IP invalide pour classful).")


def _mask_to_prefix(mask: str) -> int:
    """
    Convertit un masque '/n' ou '255.255.255.0' vers un entier préfixe.
    Vérifie la contiguïté et la plage /8.. /30.
    """
    mask = mask.strip()
    if mask.startswith("/"):
        # Notation CIDR
        try:
            prefix = int(mask[1:])
        except ValueError:
            raise NetcalcError("Préfixe invalide (format attendu: /n).")
        _validate_prefix_range(prefix)
        return prefix
    else:
        # Masque pointé : n'accepte que les masques contigus connus
        if mask not in MASK_TO_PREFIX:
            raise NetcalcError("Masque pointé invalide ou non contigu (ex: 255.10.40.0 est interdit).")
        prefix = MASK_TO_PREFIX[mask]
        _validate_prefix_range(prefix)
        return prefix


def _parse_network(ip_str: str, mask: str | None, mode: str) -> IPv4Network:
    """
    Valide IP/mode/masque selon les contraintes et renvoie un IPv4Network.
    - IPv4 uniquement
    - Masques contigus
    - /8 .. /30
    - En classful: impose le masque de la classe (A/B/C)
    """
    # 1) IP valide & IPv4 uniquement
    try:
        ipa = ip_address(ip_str)
    except Exception as e:
        raise NetcalcError(f"IP invalide: {e}")
    if not isinstance(ipa, IPv4Address):
        raise NetcalcError("Seul IPv4 est supporté.")

    # 2) Mode valide
    if mode not in {"classless", "classful"}:
        raise NetcalcError("Mode invalide (classless|classful).")

    # 3) Détermination du prefix selon le mode
    if mode == "classful":
        # a) Vérifie la classe A/B/C et récupère le prefix par défaut
        default_prefix = _default_classful_prefix_and_guard(ip_str)

        # b) Si aucun masque fourni -> impose le masque par défaut de la classe
        if mask is None or mask.strip() == "":
            prefix = default_prefix
        else:
            # c) Si un masque est fourni, il doit être EXACTEMENT celui de la classe
            provided_prefix = _mask_to_prefix(mask)  # vérifie aussi la plage /8.. /30
            if provided_prefix != default_prefix:
                # >>> IMPORTANT: message avec masque décimal pointé (pas /x)
                raise NetcalcError(
                    f"En mode classful, le masque doit être celui de la classe: {_prefix_to_mask(default_prefix)}."
                )
            prefix = default_prefix
    else:
        # mode classless: un masque est requis (CIDR ou pointé contigu) et doit rester /8.. /30
        if mask is None or mask.strip() == "":
            raise NetcalcError("Masque requis en mode classless.")
        prefix = _mask_to_prefix(mask)

    # 4) Construire le réseau à partir de l'IP (hôte) et du prefix (strict=False = accepte IP hôte)
    cidr = f"{ip_str}/{prefix}"
    try:
        return ip_network(cidr, strict=False)
    except Exception as e:
        raise NetcalcError(f"Combinaison IP/masque invalide: {e}")


def compute_network_info(ip_str: str, mask: str | None = None, mode: str = "classless") -> dict:
    """
    Fonctionnalité 1 : calculer réseau/broadcast et bornes hôtes (uniquement ce qui est utile).
    Retourne:
      - network, broadcast
      - prefixlen (entier)
      - mask (décimal pointé)
      - mask_display (ce qu'il faut afficher: classful -> décimal pointé, classless -> '/x')
      - first_host, last_host, hosts_count
    Contraintes intégrées: IPv4 uniquement, /8.. /30, masques contigus, classful A/B/C.
    """
    net = _parse_network(ip_str, mask, mode)

    network = net.network_address
    broadcast = net.broadcast_address
    prefixlen = net.prefixlen
    mask_str = _prefix_to_mask(prefixlen)  # décimal pointé systématique
    num = net.num_addresses  # >= 4 garanties par la plage /8.. /30

    # Calcul direct (pas d'itération sur les hôtes -> performant)
    first_host_int = int(network) + 1
    last_host_int  = int(broadcast) - 1

    mask_display = mask_str

    return {
        "ip_input": ip_str,
        "mode": mode,
        "network": str(network),
        "broadcast": str(broadcast),
        "prefixlen": prefixlen,  # <-- La clé standardisée et toujours présente
        "mask_display": mask_display,
        "first_host": str(IPv4Address(first_host_int)),
        "last_host": str(IPv4Address(last_host_int)),
        "hosts_count": num - 2,
    }

    """if mode == "classless":
        return {
            "ip_input": ip_str,
            "mode": mode,
            "network": str(network),
            "broadcast": str(broadcast),
            "prefix (uniquement classless)": prefixlen,  # utile en interne / pour export
            # "mask": mask_str,            # décimal pointé
            "mask_display": mask_display,  # ce qu'il faut afficher à l'utilisateur
            "first_host": str(IPv4Address(first_host_int)),
            "last_host": str(IPv4Address(last_host_int)),
            "hosts_count": num - 2,
        }
    else:
        return {
            "ip_input": ip_str,
            "mode": mode,
            "network": str(network),
            "broadcast": str(broadcast),
            #"mask": mask_str,            # décimal pointé
            "mask_display": mask_display,# ce qu'il faut afficher à l'utilisateur
            "first_host": str(IPv4Address(first_host_int)),
            "last_host": str(IPv4Address(last_host_int)),
            "hosts_count": num - 2,
        }"""


def check_ip_membership(ip_str: str, network_ip: str, mask: str | None, mode: str = "classless") -> dict:
    """
    Fonctionnalité 2 : vérifier si ip_str ∈ réseau(network_ip/mask) et renvoyer les bornes hôtes.
    Les mêmes contraintes s'appliquent (IPv4, masques contigus, /8.. /30, classful A/B/C).
    """
    # Réseau de référence (valide selon les règles)
    net = _parse_network(network_ip, mask, mode)

    # IP à vérifier (IPv4 only)
    try:
        ipa = ip_address(ip_str)
    except Exception as e:
        raise NetcalcError(f"IP à vérifier invalide: {e}")
    if not isinstance(ipa, IPv4Address):
        raise NetcalcError("Seul IPv4 est supporté.")

    in_net = ipa in net
    info = compute_network_info(network_ip, mask, mode)  # Renvoie aussi mask/mask_display

    return {"in_network": in_net, **info}