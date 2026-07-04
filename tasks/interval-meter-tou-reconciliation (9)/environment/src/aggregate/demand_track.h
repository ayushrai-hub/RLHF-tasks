#ifndef TOU_DEMAND_TRACK_H
#define TOU_DEMAND_TRACK_H

typedef struct {
    double running_sum;
    int sample_count;
} DemandTrack;

void demand_track_reset(DemandTrack *track);
void demand_track_note(DemandTrack *track, double interval_kw);
double demand_track_finalize(const DemandTrack *track);

#endif
