from typing import Iterator, Any
import json
import time
import random

import pydantic
import requests


def make_request(method: str, addr: str, path: str, **kwargs) -> requests.Response:
    res = requests.request(method, f"{addr}/{path}", **kwargs)
    res.raise_for_status()
    return res

class Cmd(pydantic.BaseModel):
    key: str
    val: str
    ver: int

class KVStore:
    def __init__(self, addr: str = "http://localhost:4000"):
        self.addr = addr

    def get(self, key: str) -> Cmd:
        return Cmd.model_validate_json(make_request("GET", self.addr, f"kvstore/{key}").text)

    def set(self, key: str, val: str, ver: int):
        make_request("PUT", self.addr, f"kvstore/{key}", data=json.dumps({"val": val, "ver": ver}))

    def keys(self) -> list[str]:
        return json.loads(make_request("GET", self.addr, "kvstore/").text)

class KVStoreDict:
    def __init__(self, addr: str = "http://localhost:4000"):
        self.kvstore = KVStore(addr)

    def __getitem__(self, key: str) -> Any:
        val = self.kvstore.get(key).val
        if len(val) == 0:
            return None
        return json.loads(val)

    def __setitem__(self, key: str, val: Any):
        if val is None:
            val_s = ""
        else:
            val_s = json.dumps(val)
        wait = 0.001
        while True:
            try:
                self.kvstore.set(key, val_s, self.kvstore.get(key).ver + 1)
                return
            except requests.exceptions.HTTPError as e:
                time.sleep(wait * random.random())
                wait *= 2

    def keys(self) -> list[str]:
        return self.kvstore.keys()

    def __delitem__(self, key: str):
        self.__setitem__(key, None)

    def values(self) -> Iterator[str]:
        for key in self.keys():
            yield self.__getitem__(key)

    def items(self) -> Iterator[tuple[str, str]]:
        for key in self.keys():
            yield key, self.__getitem__(key)

    def __dict__(self) -> dict[str, str]:
        return dict(self.items())

    def __repr__(self) -> str:
        key_str = ",".join(map(lambda s: f"\"{s}\"", self.keys()[:5]))
        return f"KVStoreDict(keys=[{key_str}, ...])"

kv = KVStoreDict()