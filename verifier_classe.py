from ipaddress import IPv4Network, IPv4Address
from enum import Enum

# Enumération
class ClasseIPV4(Enum):
    PAS_DE_CLASSE = "pas de classe"
    CLASSE_RESERVE = "classe réservé"
    CLASSE_CLASSLESS = "classless"
    CLASSE_A = "classe A"
    CLASSE_B = "classe B"
    CLASSE_C = "classe C"

# Fonctions
def ipv4_valide(ip: str) -> bool:
    try:
        IPv4Address(ip)
        return True
    except ValueError:
        return False

def verifie_classfull(reseau: IPv4Network) -> ClasseIPV4:
    if reseau is None:
        return ClasseIPV4.PAS_DE_CLASSE

    ip = reseau.network_address
    prefix = reseau.prefixlen

    if ip < IPv4Address("1.0.0.0") or (IPv4Address("127.0.0.0") <= ip < IPv4Address("128.0.0.0")):
        return ClasseIPV4.CLASSE_RESERVE
    elif IPv4Address("1.0.0.0") <= ip < IPv4Address("127.0.0.0") and prefix == 8:
        return ClasseIPV4.CLASSE_A
    elif IPv4Address("128.0.0.0") <= ip < IPv4Address("192.0.0.0") and prefix == 16:
        return ClasseIPV4.CLASSE_B
    elif IPv4Address("192.0.0.0") <= ip < IPv4Address("224.0.0.0") and prefix == 24:
        return ClasseIPV4.CLASSE_C
    elif IPv4Address("224.0.0.0") <= ip < IPv4Address("240.0.0.0") and prefix == 8:
        return ClasseIPV4.CLASSE_RESERVE
    elif IPv4Address("240.0.0.0") <= ip < IPv4Address("255.255.255.255") and prefix == 8:
        return ClasseIPV4.CLASSE_RESERVE
    else:
        return ClasseIPV4.CLASSE_CLASSLESS