import ncs
import binascii


class CiscoType7:
    '''
    This is used to encrypt the ISIS password.
    Simplified version of passlib.handlers.cisco:
    https://foss.heptapod.net/python-libs/passlib/-/blob/branch/stable/passlib/handlers/cisco.py
    '''

    @staticmethod
    def _cipher(data, salt):
        '''xor static key against data - encrypts & decrypts'''
        key = 'dsfd;kfoA,.iyewrkldJKDHSUBsgvca69834ncxv9873254k;fg87'
        key_size = 53
        return bytes([value ^ ord(key[(salt + idx) % key_size]) for idx, value in enumerate(data)])

    @classmethod
    def decode(cls, hash):
        salt = int(hash[:2])
        checksum = hash[2:]
        data = binascii.unhexlify(checksum.encode('ascii'))
        return cls._cipher(data, salt).decode('utf-8')

    @classmethod
    def encode(cls, string):
        # Salt should be randomized in the range 0-15 but is set arbitrary to
        # 1 to pass the CI configuration check. Type 7 hashes are not secure anyway...
        salt = 1
        data = cls._cipher(string.encode('utf-8'), salt)
        checksum = binascii.hexlify(data).decode('ascii').upper()
        return f'{salt:02d}{checksum}'

    @classmethod
    def verify(cls, secret, hash):
        return secret == cls.decode(hash)

def generate_net_id(ip, area_id):
    '''Generate a net ID from an ip address.

    Example: 1.23.45.167 and 49.0010 returns 49.0010.0010.2304.5167.00
    '''
    convert = ip.split('.')
    # fill each ip part with '0' to get 3 digits: [1, 23, 200 0] -> [001, 023, 200, 000]
    convert = [ip_part.rjust(3, '0') for ip_part in convert]
    # concatenate all parts
    convert = ''.join(convert)
    # split every 4 digits with '.' and add start and end part
    return f'{area_id}.{convert[:4]}.{convert[4:8]}.{convert[8:]}.00'

def generate_isis_passwd(root, formatted_as_number, device_name, interface_name):
    '''returns an encrypted password for the ISIS configuration'''

    try:
        trans = ncs.maagic.get_trans(root)
        with trans.maapi.start_read_trans() as read_trans:
            device = ncs.application.get_device(read_trans, device_name)
            encrypted = device.config.router.isis.tag['OMEGA'].interface[interface_name].hello_password.encrypted
            if encrypted == None or not CiscoType7.verify(formatted_as_number, encrypted):
                encrypted = CiscoType7.encode(formatted_as_number)
    except KeyError:
        encrypted = CiscoType7.encode(formatted_as_number)

    return encrypted
