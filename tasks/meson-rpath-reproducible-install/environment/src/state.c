#include "internal.h"

struct capsule_view cap_view_from_text(const char *text) {
    struct capsule_view view;
    view.weight = capsule_weight(text);
    view.bucket = capsule_bucket_for(text);
    view.profile = capsule_catalog_profile();
    return view;
}
