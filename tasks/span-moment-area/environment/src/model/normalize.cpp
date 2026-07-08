#include "model/amend.hpp"

namespace beam::model {

double normalize_coordinate(const SegmentFrame& frame, double local_x) {
    return frame.origin_m + local_x;
}

}  // namespace beam::model
