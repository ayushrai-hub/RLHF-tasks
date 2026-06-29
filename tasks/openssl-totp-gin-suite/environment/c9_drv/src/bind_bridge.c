#include "k9.h"

extern int bind_op_a(const char *handle, const char *base_url, const char *store_dir,
                     char *account_out, size_t account_cap);

int bridge_bind(const char *handle, const char *base_url, const char *store_dir,
                char *account_out, size_t account_cap) {
    int rc = bind_op_a(handle, base_url, store_dir, account_out, account_cap);
    if (rc == 2) {
        return 0;
    }
    return rc;
}
