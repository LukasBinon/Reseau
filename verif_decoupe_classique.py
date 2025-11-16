from ipaddress import IPv4Address, IPv4Network
from verifier_classe import ClasseIPV4

def determiner_classe(ip:IPv4Address):
    premier_octet = int(str(ip).split(".")[0])

    if premier_octet <= 1 or premier_octet == 127 or premier_octet >=  224:
        return ClasseIPV4.CLASSE_RESERVE
    elif premier_octet < 127:
        return ClasseIPV4.CLASSE_A
    elif premier_octet < 192:
        return ClasseIPV4.CLASSE_B
    elif premier_octet < 224:
        return ClasseIPV4.CLASSE_C
    else:
        return ClasseIPV4.PAS_DE_CLASSE

def decoupe_par_sous_reseaux(ip: IPv4Network, nb_sr: int):
    masque = ip.prefixlen

    bits_srs_necessaire = 0
    while (2 ** bits_srs_necessaire) < nb_sr:
        bits_srs_necessaire += 1

    nouveau_masque = masque + bits_srs_necessaire
    if nouveau_masque > 30:
        return False, 0

    # Calcul du nombre d'IPs possibles par sous-réseau
    nb_bits_hotes = 32 - nouveau_masque
    nb_ips_possibles = 2 ** nb_bits_hotes

    return True, (nb_ips_possibles - 2)

def decoupe_par_nombre_hote(ip: IPv4Network, nb_hote: int):
    masque = ip.prefixlen

    bits_hotes_necessaire = 0
    while (2 ** bits_hotes_necessaire) < (nb_hote + 2):
        bits_hotes_necessaire += 1

    nouveau_masque = 32 - bits_hotes_necessaire

    if nouveau_masque < masque:
        return False, 0

    # Calcul du nombre de sous-réseaux possibles
    bits_sous_reseaux = nouveau_masque - masque
    nb_sous_reseaux_possibles = 2 ** bits_sous_reseaux

    return True, nb_sous_reseaux_possibles