from __future__ import annotations

from pydantic import BaseModel, ConfigDict
import pydantic


class M(BaseModel):
    model_config = ConfigDict(extra="allow")
    a: int = 1


if __name__ == "__main__":
    print("pydantic", pydantic.__version__)
    m = M.model_validate({"a": 2, "extraKey": {"x": 1}, "b": 3})
    print("extra stored", getattr(m, "__pydantic_extra__", None))
    print("dump default", m.model_dump())
    print("dump json", m.model_dump(mode="json"))
