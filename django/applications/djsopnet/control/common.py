from numpy import int64, uint64

def safe_split(tosplit, name='data', delim=','):
    """ Tests if $tosplit evaluates to true and if not, raises a value error.
    Otherwise, it the result of splitting it is returned.
    """
    if not tosplit:
        raise ValueError("No %s provided" % name)
    return tosplit.split(delim)


def hash_to_id(hash_uint64):
    """ Casts a string or uint representation of an unsigned 64-bit hash value
    to a signed long long value that matches Postgres' bigint. E.g.,
      >>> hash_to_id("9223372036854775808")
      -9223372036854775808
    """
    return int64(uint64(hash_uint64))


def id_to_hash(id_int64):
    """ Casts a string or int representation of an signed 64-bit hash value to a
    unsigned long value that matches sopnet's size_t hash,
      >>> id_to_hash("-9223372036854775808")
      9223372036854775808
    """
    return str(uint64(int64(id_int64)))
