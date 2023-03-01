Vendoring is automated via the vendoring tool from the content of ./vendor.txt. `pip install vendoring; vendoring sync . -v` to sync packages.

Currently, we only vendoring pip since users may have different pip versions, and pip naming it's module as `_internal`, and ..balabala.. so vendoring technology is introduced, not in the happy way.
