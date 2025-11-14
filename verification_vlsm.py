import ipaddress

def calculer_bloc_ip(nb_ips_utilisables: int) -> int:
    """
    calcul la taille du bloc (puissance de 2) nécessaire pour un nombre d'IP utilisables.
    La puissance de 2 suivante est 128 (bloc /25).
    """
    if nb_ips_utilisables <= 0:
        raise ValueError("Le nombre d'IP doit être positif.")

    # +2 pour l'adresse réseau et l'adresse de broadcast
    total_requis = nb_ips_utilisables + 2

    # le bloc minimum standard est un /30 (4 IPs) pour 2 hôtes
    if total_requis < 4:
        total_requis = 4

    # calcule le nombre de bits hôte nécessaires (ceil(log2(total_requis)))
    h_bits = (total_requis - 1).bit_length()

    # la taille du bloc est 2^h_bits
    taille_bloc = 2 ** h_bits
    return taille_bloc


def verifier_possibilite_vlsm(reseau_de_base_str: str, masque_str: str | None, besoins_list: list[int]):
    """
    Vérifie si une liste de besoins (nb d'IP) peut tenir dans un réseau de base.
    besoins_list: une liste d'entiers [100, 50, 30]
    """
    # 1 parse le réseau de base
    try:
        net_str = reseau_de_base_str.strip()
        masque_clean = masque_str.strip() if masque_str else None

        if "/" in net_str:
            # Cas 1: L'IP a un CIDR, mais le champ masque est AUSSI rempli
            if masque_clean:
                raise ValueError(
                    "Conflit de saisie : Fournissez le masque DANS le réseau de base (ex: 192.168.1.0/24) "
                    "OU dans le champ 'Masque', mais PAS les deux."
                )
            #l'IP a un CIDR, le champ masque est vide
            pass
        else:
            #l'IP n'a pas de CIDR, le champ masque est rempli
            if masque_clean:
                if masque_clean.startswith("/"):
                    net_str = f"{net_str}{masque_clean}"
                else:
                    net_str = f"{net_str}/{masque_clean}"
            #L'IP n'a pas de CIDR, le champ masque est vide
            else:
                raise ValueError("Masque manquant pour le réseau de base.")

        # 'net_str' est maintenant propre on peut parser
        net = ipaddress.ip_network(net_str, strict=False)
        total_ips_disponibles = net.num_addresses

    except Exception as e:

        raise ValueError(f"Réseau de base ou masque invalide : {e}")

    #  parse la liste des besoins
    if not besoins_list:
        raise ValueError("La liste des besoins ne peut être vide.")

    total_ips_requises = 0

    # calcule le total requis
    for besoin in sorted(besoins_list, reverse=True):
        try:
            taille_bloc = calculer_bloc_ip(besoin)
            total_ips_requises += taille_bloc

        except ValueError as e:
            raise ValueError(f"Besoin invalide ({besoin}) : {e}")

    #  compare
    possible = total_ips_requises <= total_ips_disponibles

    message = (
        f"Réseau de base : {net.with_prefixlen}\n"
        f"Total IPs disponibles : {total_ips_disponibles}\n"
        f"Total IPs requises: {total_ips_requises}\n"
        f"--------------------------------------------------\n"
        f"Résultat : Découpe VLSM possible : {'OUI' if possible else 'NON'}\n"
        f"--------------------------------------------------"
    )

    return possible, message