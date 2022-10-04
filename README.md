# Decreasing micropython code size

Having smaller code is always a good thing. Sometimes it is a necessity, for example when running on a micro-controller with limited flash space. Smaller code should also be quicker to execute, due to less instructions.

This is a collection of tips and tricks to reduce the compiled size of the `micropython` code.

Majority of these strategies are also automated into this tool, so one does not need to search for them manually.

One of the very few resources on this topic is [micropython docs](https://docs.micropython.org/en/latest/reference/speed_python.html#micropython-code-improvements) - even though it mainly concerns speed, some tips are common for code size efficiency.

All the examples below are real, coming from `micropython` codebase of [Trezor firmware](https://github.com/trezor/trezor-firmware) repository.

(Want to measure how big is the code in the final binary? Try out [size analysis tool](https://github.com/grdddj/binsize))

## Strategies

Overall, strategies have one thing in common - reducing the amount of instructions/bytecode that need to be compiled into the final binary/executable.

To sum up some of the lessons learned:

```
Accessing global symbols from functions is expensive.
Accessing symbol attributes is expensive.
```

which leads to a saying

```
Cache is our friend.
```

List below shows the strategies (in no particular order).

### 1. Delete unused code

Probably the easiest way to reduce the size of the code is to delete all the unused stuff (imports, functions, classes, variables... ) - or at least delete it from the resulting binary. How to search for it? Apart from doing it manually, what helps are two things:
- code editor (at least `VS Code`) highlights unused symbols - they become greyed out
- tools like [Vulture](https://pypi.org/project/vulture/) can analyze whole `python` codebase and report all possibly unused symbols

---

### 2. Import only what is needed for the code execution

Static type hints in modern `python` are a fantastic thing, but they are not without some drawbacks. When type-hinting with object from another module, this object needs to be imported - and therefore, normally, will generate some runtime and compiled overhead.

To combat this (and also to combat circular dependencies), it is possible to use `typing.TYPE_CHECKING` flag. This flag is `False` at runtime, but `True` when type-checking the code. The imports inside `if TYPE_CHECKING:` are not executed at runtime (not included into binary at compile time).

##### Before
```python
from my_module import MyObject

def my_func(obj: MyObject) -> None:
    ...
```

##### After
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from my_module import MyObject

def my_func(obj: MyObject) -> None:
    ...
```

#### Benefits

Size cost of one global import is around **8 bytes**.

---

### 3. Inline short one-time helper functions

Having a lot of small and well-documented helper functions is generally a good practice. However, each function has significant size overhead in the resulting binary.

When a function is used only once, it can be beneficial to inline it. This is especially true for short functions, which are not used anywhere else.

##### Before

```python
def derive_shelley_address(parameters: Params) -> bytes:
    header = _create_header(parameters.address_type, network_id)
    ...

def _create_header(address_type: AddressType, network_id: int) -> bytes:
    header = address_type << 4 | network_id
    return header.to_bytes(1, "little")
```

##### After

```python
def derive_shelley_address(parameters: Params) -> bytes:
    # _create_header
    header_int = parameters.address_type << 4 | network_id
    header = header_int.to_bytes(1, "little")
    ...
```

#### Benefits

Size benefit of inlining one-time function is around **50 bytes**. It depends on the amount of function arguments - the more, the bigger the size decrease. Also, those two functions can now share one local scope, which is beneficial for caching purposes (see next strategies).

#### Drawbacks

It can decrease the readability of the code. It is also then impossible to test that helper function in isolation. What would solve both these issues is compile-time magic doing the "inlining" automatically.

---

### 4. Create functions of repeating patterns

It may be a contradiction of the point above, to create more functions, but when the same logic is used many times, it can be (not only space-wise) beneficial to group it into a function.

##### Before

```python
self.prevouts = HashWriter(blake2b(outlen=32, personal=b"ZTxIdPrevoutHash"))
self.amounts = HashWriter(blake2b(outlen=32, personal=b"ZTxTrAmountsHash"))
...
self.outputs = HashWriter(blake2b(outlen=32, personal=b"ZTxIdOutputsHash"))
```

##### After

```python
def blake_hash_writer_32(personal: bytes) -> HashWriter:
    return HashWriter(blake2b(outlen=32, personal=personal))

self.prevouts = blake_hash_writer_32(b"ZTxIdPrevoutHash")
self.amounts = blake_hash_writer_32(b"ZTxTrAmountsHash")
...
self.outputs = blake_hash_writer_32(b"ZTxIdOutputsHash")
```

#### Benefits

The more expensive the operation is, the bigger the size benefit. Also it is more apparent that all the steps are really the same in all places.

---

### 5. Replace series of calls with a loop

When there is an uninterrupted sequence of the same calls, just with different arguments, it can be beneficial to replace it with a loop.

##### Before

```python
write_uint32_le(w, tx.version | OVERWINTERED)  # nVersion | fOverwintered
write_uint32_le(w, tx.version_group_id)  # nVersionGroupId
write_uint32_le(w, tx.branch_id)  # nConsensusBranchId
write_uint32_le(w, tx.lock_time)  # lock_time
write_uint32_le(w, tx.expiry)  # expiryHeight
```

##### After

```python
for num in (
    tx.version | _OVERWINTERED,  # nVersion | fOverwintered
    tx.version_group_id,  # nVersionGroupId
    tx.branch_id,  # nConsensusBranchId
    tx.lock_time,  # lock_time
    tx.expiry,  # expiryHeight
):
    write_uint32_le(w, num)
```

---

### 6. Not setting values through if-elif-else

If applicable (when always comparing the same thing), a `dict` may be more efficient than a long `if-elif-else` chain.

##### Before

```python
if rotation == 0:
    label = "north"
elif rotation == 90:
    label = "east"
elif rotation == 180:
    label = "south"
elif rotation == 270:
    label = "west"
else:
    raise wire.DataError("Unsupported display rotation")
```

##### After

```python
label = {
    0: "north",
    90: "east",
    180: "south",
    270: "west",
}.get(rotation)
if label is None:
    raise DataError("Unsupported display rotation")
```

In very simple cases, ternary operator can be even more space-efficient:

```python
if msg.fee.change > 0:
    action = "increase"
else:
    action = "decrease"
```

vs

```python
action = "increase" if msg.fee.change > 0 else "decrease"
```

---

### 7. Cache any frequent attribute access

Attribute access is expensive, so when we do it repeatedly, we could cache the result into one variable.

##### Before
(focus on `msg.address_n`)

```python
async def get_address(ctx: Context, msg: GetAddress) -> Address:
    await validate(ctx, msg.address_n)
    node = derive(msg.address_n)
    address = to_str(msg.address_n)
    return Address(address=address)
```

##### After

```python
async def get_address(ctx: Context, msg: GetAddress) -> Address:
    address_n = msg.address_n  # cache

    await validate(ctx, address_n)
    node = derive(address_n)
    address = to_str(address_n)
    return Address(address=address)
```

It works well even with methods:

```python
my_list = []

my_list.append(...)
...
my_list.append(...)
```

vs

```python
my_list = []
my_list_append = my_list.append  # cache

my_list_append(...)
...
my_list_append(...)
```

#### Benefits

The more the attribute lookup was used, the bigger the saving. It saves around  **2 bytes** per one replaced lookup (when replacing 4 or more usages).

#### Drawbacks

For caching methods, it worsens their readability in code editor (`my_list.append` has object and method differentiated by color, while `my_list_append` is only a variable).

---

### 8. Cache frequently accessed global symbol locally

Accessing global symbols (imported modules or top-level functions) is expensive. When we use it many times inside one function, it could be beneficial to store the reference in a local variable.

##### Before

```python
from trezor.messages import MessageType

def boot() -> None:
    register(MessageType.GetAddress, get_address)
    register(MessageType.GetPublicKey, get_public_key)
    ...
    register(MessageType.Ping, ping)
```

##### After

```python
from trezor.messages import MessageType

def boot() -> None:
    MT = MessageType  # cache

    register(MT.GetAddress, get_address)
    register(MT.GetPublicKey, get_public_key)
    ...
    register(MT.Ping, ping)
```

"Double win" is storing a local reference to a global attribute lookup:

```python
from trezor import wire

def validate(msg: Message) -> None:
    if msg.high_fee:
        raise wire.DataError("high_fee")
    if msg.low_fee:
        raise wire.DataError("low_fee")
    ...
```

vs

```python
from trezor import wire

def validate(msg: Message) -> None:
    DataError = wire.DataError  # cache

    if msg.high_fee:
        raise DataError("high_fee")
    if msg.low_fee:
        raise DataError("low_fee")
    ...
```

#### Benefits

The more global usages are replaced, the bigger benefit. It is roughly **1 byte** per replacement when replacing 5 or more usages.

---

### 9. Import symbols only in the one function where it is used

When some imported symbol is used only in one function from the module, it is beneficial to import it locally just in that single function instead of creating a global import.

##### Before

```python
from trezor.crypto.hashlib import sha256

def get_tx_hash(w: HashWriter) -> bytes:
     d = w.get_digest()
     return sha256(sha256(d).digest()).digest()
```

##### After

```python
def get_tx_hash(w: HashWriter) -> bytes:
    from trezor.crypto.hashlib import sha256

    d = w.get_digest()
    return sha256(sha256(d).digest()).digest()
```

#### Benefits

The more times the symbol is used in that function, the more space-beneficial it is to import it just there (as it creates a local symbol, not a global one).  For each usage of local import, around **2-3 bytes** are saved.

#### Drawbacks

This way not all the imports are on the top and it is therefore harder to see all the dependencies of the module. Also when later adding another function using this symbol, we need to decide whether to import it also locally there, or do it globally.

---

### 10. Use `const` for global constants

Creating a constant is more costly than to define a normal number, but it saves a lot in places which use this constant.

##### Before

```python
HASH_LENGTH = 32
SLIP_44_ID = 123
LOCAL_ONLY = 456
```

##### After

```python
from micropython import const

HASH_LENGTH = const(32)
SLIP_44_ID = const(123)
_LOCAL_ONLY = const(456)
```

One extra benefit of using `const()` is when the variable is used only in module where it is defined. In that case, prepending a variable name with `_` will tell `micropython` that it does not need to be included in the public module dictionary. This saves around **4 bytes**.  More details in [micropython docs](https://docs.micropython.org/en/v1.9.3/wipy/reference/constrained.html#execution-phase).

---

### 11. Import frequently used symbols directly

To avoid the need of attribute lookups on imported modules, importing the used symbols directly can be beneficial when that symbol is used many times in more than one function.

##### Before

```python
from trezor import wire
import trezorui2

def show_group_share_success():
    ...
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled

def continue_recovery():
    ...
    if result is not trezorui2.CONFIRMED:
        raise wire.ActionCancelled
```

##### After

```python
from trezor.wire import ActionCancelled
from trezorui2 import CONFIRMED

# CONFIRMED = trezorui2.CONFIRMED  # cache  # second option

def show_group_share_success():
    ...
    if result is not CONFIRMED:
        raise ActionCancelled

def continue_recovery():
    ...
    if result is not CONFIRMED:
        raise ActionCancelled
```

### 12. Do not use keyword arguments

Calling functions with keyword arguments is nice (hello `Rust`), but it turns out it costs more space than with positional arguments.

##### Before

```python
mosaic = MosaicLevy(
    type=Mosaic.ABC,
    fee=10,
    namespace="dim",
    mosaic="coin",
)
```

##### After

```python
mosaic = MosaicLevy(  # levy
    Mosaic.ABC,  # type
    10,  # fee
    "dim",  # namespace
    "coin",  # mosaic
)
```

#### Benefits

It saves **3 bytes** per one kwarg pair.

#### Drawbacks

It can decrease readability of what each argument means, especially when there are many of them. It can be therefore good to include comments with the names of the arguments.

---

### 13. Do not use small classes to hold data for a short time

When data have only short-term duration (are not passed to other modules, etc.), the class may be replaced by a tuple holding just the raw data.

Defining class and creating an instance are both quite costly, so avoiding it saves space. Tuples do not have this cost.

##### Before

```python
class RippleField:
    def __init__(self, type: int, key: int) -> None:
        self.type: int = type
        self.key: int = key

FIELDS: list[RippleField] = [
    RippleField(type=FIELD_TYPE_ACCOUNT, key=1),
    RippleField(type=FIELD_TYPE_ACCOUNT, key=3),
    ...
    RippleField(type=FIELD_TYPE_INT32, key=27),
]

def serialize(w: Writer):
    for field in FIELDS:
        write(w, field)

def write(w: Writer, field: RippleField) -> None:
    type = field.type
    key = field.key
    ...
```

##### After

```python
if TYPE_CHECKING:
    RippleField = tuple[int, int]

FIELDS: list[RippleField] = [
    (FIELD_TYPE_ACCOUNT, 1),
    (FIELD_TYPE_ACCOUNT, 3),
    ...
    (FIELD_TYPE_INT32, 27),
]

def serialize(w: Writer):
    for field in FIELDS:
        write(w, field)

def write(w: Writer, field: RippleField) -> None:
    type = field[0]
    key = field[1]
    ...
```

#### Drawbacks

It worsens the readability/reliability due the need of using number subscripting (`field[0]`) to access the data. It can be therefore good to define a type alias for the tuple to have a static analysis.

---

### 14. Effectively store bigger data

In memory-constrained environments we sometimes need to work with data-sets that cannot even fit RAM in their entirety. For those cases the data need to be stored in flash and accessed sequentially, which can cost a lot of space.

Yielding iterators of tuples turned out to be the most effective way. Some higher function will loop through them and can do something on each element.

(Using tuples is more efficient than classes, as already discussed above. Class can be constructed by the higher function.)

##### Before

```python
class TokenInfo:
    def __init__(self, symbol: str, decimals: int) -> None:
        self.symbol = symbol
        self.decimals = decimals

def token_by_chain_address(address: bytes) -> TokenInfo:
    if address == b"\x4e\x84...":
        return TokenInfo("$FFC", 18)
    if address == b"\x7d\xd7...":
        return TokenInfo("$TEAK", 18)
    ...
```

##### After

```python
def token_by_chain_address(address: bytes) -> TokenInfo:
    for t in _token_iterator():
        if address == t[0]:
            return TokenInfo(t[1], t[2])

def _token_iterator() -> Iterator[tuple[bytes, str, int]]:
    yield (  # address, symbol, decimals
        b"\x4e\x84...",
        "$FFC",
        18,
    )
    yield (  # address, symbol, decimals
        b"\x7d\xd7..",
        "$TEAK",
        18,
    )
    ...
```

## Conclusion

Using the strategies above, it was possible to shrink the compiled size of [Trezor firmware](https://github.com/trezor/trezor-firmware)'s `micropython` code by around **10 %**.
