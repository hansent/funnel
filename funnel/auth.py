from passlib.context import CryptContext

pwd_context = CryptContext(
    # replace this list with the hash(es) you wish to support.
    # this example sets pbkdf2_sha256 as the default,
    # with support for legacy des_crypt hashes.
    schemes=["bcrypt", "sha512_crypt", "pbkdf2_sha256"],
    default="bcrypt",

    # vary rounds parameter randomly when creating new hashes...
    all__vary_rounds = 0.1,

    # set the number of rounds that should be used...
    # appropriate values may vary for different schemes.
    pbkdf2_sha256__default_rounds = 8000,
)
