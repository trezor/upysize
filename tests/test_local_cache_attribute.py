from src.upysize.strategies.local_cache_attribute import local_cache_attribute

CODE = """\
def abc(msg):
    return msg.tre


def my_func(ctx, msg):
    # comment not to take msg.abc
    assert msg.abc is not None
    abc(msg.abc)
    x = msg.abc.xyz
    return MyMessage(abc=msg.abc)


def nonmutating_func(ctx, msg):
    assert msg.xyz.abc is not None
    msg.xyz.abc = 1
    abc(msg.xyz.abc)
    x = msg.xyz.abc
    return MyMessage(abc=msg.xyz.abc)


def mutating_func1(ctx, msg):
    assert msg.abc is not None
    msg.abc = 1
    return MyMessage(abc=msg.abc)


def mutating_func2(ctx, msg):
    assert msg.abc is not None
    msg.abc += 1
    abc(msg.abc)
    return MyMessage(abc=msg.abc)


def reassigned_func(ctx, msg):
    res = get_res(0)
    show(res.abc)
    if not res.abc:
        error()

    res = get_res(1)
    show(res.abc)
    if not res.abc:
        error()
"""


def test_local_cache_attribute():
    res = local_cache_attribute(CODE, threshold=3)
    assert len(res) == 5

    assert res[0].func.name == "my_func"
    assert res[0].cache_candidate.cache_string == "msg.abc"
    assert res[0].cache_candidate.amount == 4
    assert res[0].attribute_mutated is False
    assert res[0].symbol_assigned is False
    assert res[0].saved_bytes() == 7

    assert res[1].func.name == "nonmutating_func"
    assert res[1].cache_candidate.cache_string == "msg.xyz"
    assert res[1].cache_candidate.amount == 5
    assert res[1].attribute_mutated is False
    assert res[1].symbol_assigned is False
    assert res[1].saved_bytes() == 10

    assert res[2].func.name == "mutating_func1"
    assert res[2].cache_candidate.cache_string == "msg.abc"
    assert res[2].cache_candidate.amount == 3
    assert res[2].attribute_mutated is True
    assert res[2].symbol_assigned is False
    assert res[2].saved_bytes() == 4

    assert res[3].func.name == "mutating_func2"
    assert res[3].cache_candidate.cache_string == "msg.abc"
    assert res[3].cache_candidate.amount == 4
    assert res[3].attribute_mutated is True
    assert res[3].symbol_assigned is False
    assert res[3].saved_bytes() == 7

    assert res[4].func.name == "reassigned_func"
    assert res[4].cache_candidate.cache_string == "res.abc"
    assert res[4].cache_candidate.amount == 4
    assert res[4].attribute_mutated is False
    assert res[4].symbol_assigned is True
    assert res[4].saved_bytes() == 7
