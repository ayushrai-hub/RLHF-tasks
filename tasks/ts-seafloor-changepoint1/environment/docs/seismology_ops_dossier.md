# Pacific Seafloor Observatory Network (PSON)
## Operations and Calibration Reference Dossier
### Revision 7.4 — January 2024
### Compiled by: PSON Data Management Group, Oregon State University / UW MBARI Joint Program

---

## Executive Summary

The Pacific Seafloor Observatory Network (PSON) is a multi-institutional array of permanently installed seafloor pressure, tilt, and temperature sensors deployed along the Juan de Fuca Ridge system and adjacent Cascadia Basin environments. As of the preparation of this revision, the network comprises five active monitoring stations: AXID01, AXID02, NEMO01, JUAN01, and COAX01, each contributing continuous telemetry to the consortium data archive. A sixth station, NEMO02, was placed in standby mode following a flooded junction box in October 2023 and is omitted from the active calibration tables in this revision; its historical data remain accessible via the archive portal.

This dossier consolidates the calibration coefficients, deployment history, signal processing guidelines, known anomalies, and event-detection parameters for each active station. It is intended to be the authoritative reference for any automated or manual analysis of sensor time series data stored in the network database. Personnel performing algorithmic event detection, outlier screening, or catalog compilation should rely on the station-specific parameters documented herein rather than applying generic network-wide assumptions.

The January 2024 update incorporates revised calibration results from the September 2023 ROV servicing cruise aboard R/V Thomas G. Thompson, corrects two typographical errors in the COAX01 gain coefficient noted by Dr. Yuki Tanabe during her audit in December 2023, and appends the maintenance log entries for the fourth quarter of 2023. It also formalizes the Bayesian change-point scoring procedure that has been in informal use among the PSON analysis team since mid-2022.

Network operations remain fundamentally sound across all active stations. Data completeness for calendar year 2023 was 98.3% for pressure series, 97.1% for tilt, and 99.4% for temperature, representing marginal improvements over the prior year's figures. The main operational challenge in 2023 was telemetry intermittency at JUAN01 during the August 2023 swarm sequence, which introduced a 14-hour gap in that station's pressure record; the timing and magnitude of the gap are documented in the JUAN01 station section and in the maintenance log.

Researchers using PSON data for published analyses are reminded that all primary calibration work is conducted by the PSON Calibration Working Group and that any deviation from the parameters provided in this document requires explicit approval and documentation.

---

## 1. Network Architecture and Operational Context

### 1.1 Geographic Scope and Scientific Motivation

The PSON array spans approximately 580 kilometers of the eastern Pacific seafloor, from the southern flanks of Axial Seamount at approximately 45.95° N to the Juan de Fuca Ridge vent field region near 47.97° N, with a further western outpost at the Cascadia Basin site designated COAX01. The network was designed in the early 2010s to address a fundamental observational gap in understanding slow-slip events (SSEs) along the Cascadia subduction zone and at the ridge-transform intersections that punctuate the Juan de Fuca spreading system.

The scientific case for real-time, continuous, multi-station pressure monitoring at these sites rests on the recognition that creep events, episodic tremor and slip, and volcano-tectonic seismic sequences in this region produce geodetic signals that propagate into the water column as pressure perturbations at seafloor depth. A vertical displacement of the seafloor of even a few centimeters, occurring over hours to days, produces a pressure anomaly detectable by modern quartz-resonator ocean bottom pressure gauges if the noise floor of the instrument is sufficiently low and if appropriate detrending procedures are applied to remove the dominant oceanographic background signals: tidal loading, mesoscale oceanic eddies, atmospheric loading, and long-period swell.

Early single-station observations at Axial Seamount documented the feasibility of this approach during the April 2011 eruption sequence. The deflation of the Axial caldera produced a pressure drop of more than 30 kPa at the summit sensor, far larger than any expected noise source, and validated both the instrument design and the interpretation framework. Subsequent work during the 2015 and 2022 eruption cycles confirmed these results and extended the monitoring to the interseismic period where smaller but scientifically important deformation events were detectable at the network level.

The current network architecture evolved through several funding cycles supported by the National Science Foundation's Ocean Sciences Division, the Gordon and Betty Moore Foundation, and contributions from the Ocean Networks Canada consortium. Each expansion phase introduced new sensors or updated existing deployments to take advantage of improvements in transducer technology, battery longevity, and acoustic modem reliability.

### 1.2 Sensor Technology Overview

All five active PSON pressure stations deploy Paroscientific 8B7000-I series digiquartz transducers as their primary measurement element. These instruments resolve pressure changes of approximately 0.001 kPa over integration periods of 60 seconds and exhibit long-term stability better than 0.02% of full-scale over multi-year deployment intervals, provided the sensors are maintained at near-constant ambient temperature — a condition largely satisfied at seafloor depths where temperature variability is subdued and governed primarily by geothermal and diffuse hydrothermal fluxes rather than surface-forced advection.

Factory calibration of each Paroscientific unit is performed by the manufacturer before shipment using a dead-weight tester referenced to NIST standards. The factory calibration coefficients are burned into the instrument's onboard firmware and are applied automatically during the primary digital conversion; however, the PSON network applies an additional secondary calibration layer to account for small depth-dependent pressure offsets, electronic component drift since the factory test, and systematic effects introduced by the titanium housing and the mechanical interface between the transducer port and the lander frame. These secondary correction factors are the gain and offset terms documented individually for each station in Sections 3 through 7 of this dossier.

The secondary calibration relationship is linear and takes the form: calibrated_pressure = raw_sensor_output × gain + offset, where raw_sensor_output is the value stored in the network database, gain is a dimensionless multiplicative factor, and offset is additive in kilopascals. All calibrated pressures are thus in units of kilopascals in the absolute gauge scale. The calibration parameters were most recently updated following the September 2023 servicing cruise, which deployed a secondary reference CTD alongside each station's pressure port for an 18-hour intercomparison period.

Tilt sensors are deployed at the two Axial Seamount stations, AXID01 and AXID02, using Applied Geomechanics Model 702 biaxial borehole tiltmeters retrofitted to shallow seafloor installations. The tilt data are stored in the database in units of radians in the X and Y channels of the instrument's body frame, which is aligned approximately with the north-south and east-west horizontal axes at Axial's summit. Because tilt signals associated with volcanic inflation and slow-slip events are typically at the level of a few micro-radians or less, the tilt channels serve primarily as a complementary diagnostic for corroborating pressure-derived event candidates rather than as primary detection channels. Temperature sensors at all stations use an Aanderaa 4060 thermistor integrated with each lander frame.

### 1.3 Database Structure and Telemetry Pipeline

Raw sensor data are transmitted acoustically to a surface mooring or via a fiber-optic cable connection (COAX01 only) to the shore-side archiving node at the University of Washington. AXID01, AXID02, and NEMO01 use acoustic modems for daily burst transmissions; JUAN01 uses a combination of acoustic modem and scheduled satellite link for redundancy; COAX01 benefits from a low-bandwidth fiber connection providing near-real-time data transfer at 115 baud.

Upon receipt at the shore node, data are unpacked from the modem packet stream, quality-flagged by automated range and continuity checks, and inserted into the relational database with a 10-minute sample interval timestamp in ISO 8601 UTC format. The database schema records each measurement as a row in the readings table with columns: station identifier, sensor type string, timestamp, raw numerical value, and unit string. Station metadata reside in the stations table and are keyed by station code.

The raw_value stored in the database always reflects the voltage-to-pressure conversion output by the instrument's onboard digital processor, prior to the application of PSON's secondary gain-and-offset calibration. The rationale for storing raw rather than calibrated values is backward compatibility: if calibration coefficients are updated following a servicing cruise, historical records do not need to be reprocessed — only the calibration parameters in this dossier change, and any downstream analysis applies the updated coefficients.

### 1.4 Slow-Slip Event Detection Framework

The standard PSON methodology for detecting slow-slip events in pressure time series follows a four-stage pipeline, the details of which are elaborated in Section 9. The stages are: (1) application of the secondary calibration to convert raw database values to calibrated kilopascal pressure, (2) detrending to remove the low-frequency background drift and tidal signal, (3) computation of robust Z-scores using the median absolute deviation as the dispersion estimator, and (4) candidate window scoring using a Bayesian log-likelihood ratio approach. Events that survive a station-specific Z-score threshold and a minimum duration test are entered as candidates in the automated catalog and subsequently reviewed for data quality flags, maintenance windows, and cross-station corroboration.

The station-specific thresholds reflect the markedly different noise characteristics of each deployment environment. Stations at Axial Seamount benefit from relatively quiet pressure conditions because the caldera's quasi-enclosed geometry damps mesoscale oceanographic pressure forcing. In contrast, COAX01, sitting on the open Cascadia Basin, experiences stronger oceanographic pressure variability and consequently requires a higher detection threshold to avoid flooding the catalog with oceanographic false positives. JUAN01 sits on the ridge crest where hydrothermal emission creates elevated temperature noise that occasionally couples into the pressure channel, motivating a distinct minimum-duration requirement at that station.

---

## 2. Station AXID01 — Axial Seamount Primary Pressure Array

### 2.1 Location, Deployment, and Physical Setting

Station AXID01 is the flagship monitoring installation of the PSON array, positioned at geographic coordinates 45.9547° N, 130.0085° W, on the south rim of the Axial Seamount caldera at a water depth of approximately 4145 meters. The station was first deployed in July 2021 as a component of the Ocean Observatories Initiative (OOI) regional cabled array expansion and has operated continuously since then with the exception of three brief outages totaling less than 30 hours.

The lander frame is a stainless steel tripod bolted to basalt outcrop using submarine epoxy anchors, oriented with the pressure port facing upward and slightly tilted 3.2° from vertical in the instrument body frame due to the irregular surface topography at the precise deployment location. The pressure port itself faces the open water column above the frame and is protected from particulate fouling by a titanium mesh screen. Two ROV interventions have been conducted at this station: the initial deployment dive in July 2021 and a servicing dive in September 2023 during which the screen mesh was cleaned of minor biofouling and the acoustic modem antenna was repositioned to improve transmission azimuth toward the surface buoy.

The surrounding seafloor geology is dominated by lobate pillow basalt flows from the 2011 eruption overlain by thin pelagic sediment. Hydrothermal activity within the caldera is concentrated along the caldera fault scarps approximately 200 meters to the north and east of AXID01's deployment site, meaning that diffuse low-temperature hydrothermal circulation is measurable at the instrument but does not produce significant thermal noise in the pressure channel at the 10-minute averaging interval used by the network.

### 2.2 Instrument Specifications and Serial Numbers

The primary pressure transducer at AXID01 is a Paroscientific 8B7000-I-001 unit, serial number 140297, rated for full-scale operation to 7000 psia (approximately 48,000 kPa) with a calibrated accuracy of ±0.01% full-scale (±4.8 kPa). In practice, the instrument performs considerably better than this specification at the static pressures encountered at its deployment depth because the measurement regime lies far below the full-scale limit and the dynamic pressure range of interest for slow-slip event detection is less than 5 kPa in peak-to-peak variation.

The biaxial tiltmeter deployed alongside the pressure sensor is an Applied Geomechanics Model 702-2G-C unit, serial number AG-0314, with a range of ±20,000 micro-radians and resolution of approximately 0.01 micro-radians at the 10-minute averaging interval. The temperature sensor is an Aanderaa 4060 unit, serial number AA-7198.

The full instrument stack, including transducer housing, electronics, battery pack, and acoustic modem unit, has a total displacement of approximately 0.8 cubic meters and a dry weight of 74 kilograms. The battery pack is designed for 36 months of autonomous operation at the nominal 10-minute sampling interval; the first battery pack was replaced during the September 2023 servicing dive, with an expected next battery service window in late 2026.

### 2.3 Secondary Calibration Coefficients

Following the September 2023 ROV servicing cruise, the PSON Calibration Working Group completed an intercomparison between AXID01's onboard sensor output and measurements from a SBE 37-SM MicroCAT CTD deployed at the same depth for 18 hours alongside the lander. The intercomparison data were analyzed by senior instrument technician Margaret Holt and reviewed by Dr. Ravi Krishnamurthy of the PSON data management group.

The result of this analysis established the secondary calibration relationship for AXID01's pressure channel. The gain correction factor is 1.0247, a value reflecting the approximately 2.4% upward scale adjustment needed to bring the Paroscientific unit's output into agreement with the SBE reference measurement. This gain arises primarily from temperature-induced sensitivity drift in the crystal resonator that was not fully characterized during the most recent factory calibration conducted in May 2021, combined with a small but consistent bias introduced by the mechanical coupling geometry between the instrument port and the lander frame. The additive pressure offset is −0.183 kilopascals, representing the zero-point shift measured at equilibrium when the lander was confirmed to be stationary relative to the seafloor. The sign convention follows the network standard: positive offset means the raw sensor reads low relative to true pressure, and a negative offset means the raw sensor reads high. In this case, the negative offset indicates that AXID01's raw output slightly overstates the true ambient pressure at equilibrium, a characteristic that has been stable since the instrument's initial deployment.

Applying these two coefficients in the standard formula — calibrated_pressure_kPa = raw_value × 1.0247 + (−0.183) — yields time series that are consistent with the long-term absolute pressure trend expected from the tidal loading model and the known bathymetric depth. The calibrated baseline pressure at AXID01 is approximately 414.5 kPa, which corresponds well to a water depth of approximately 4145 meters using the standard UNESCO seawater equation of state.

### 2.4 Signal Quality and Known Artifacts

AXID01's pressure record is among the cleanest in the PSON array, benefiting from its location inside the caldera where the above-mentioned geometric damping reduces the amplitude of mesoscale oceanographic pressure variability. Typical background noise levels in the detrended pressure series are at the level of 0.004–0.006 kPa root-mean-square in the 10-minute sampled data, which represents a favorable noise floor for detecting slow-slip event pressure anomalies of 0.1 kPa or greater.

There are two categories of known artifacts in the AXID01 record that users should be aware of. The first category is what the PSON team calls "modem ringing" — a very brief pressure spike of approximately +0.02 to +0.04 kPa lasting exactly one or two samples that occasionally appears in the record following acoustic modem transmission events. The modem's transducer generates a pressure pulse in the water column that is picked up by the nearby pressure sensor. Because these spikes are of very short duration (one or two 10-minute samples) and fall far below the minimum-duration criterion for event detection, they do not contaminate the automated catalog, but they are conspicuous in raw time series plots. They should be attributed to acoustic coupling rather than geophysical signals.

The second category of artifact is a small annual pressure anomaly of approximately 0.01–0.02 kPa that appears to be associated with biofouling of the pressure port screen mesh during the late summer and autumn months. As biological activity peaks in the overlying water column, microscale organisms and particulate organic material accumulate on the mesh screen, creating a slight restriction of flow across the pressure port that manifests as a slowly evolving offset in the calibrated record. This signal is removed by the detrending step in the standard processing pipeline, but analysts should be aware of its existence if inspecting records during August–October.

### 2.5 Event Detection Parameters

The PSON analysis team, following a review of detection performance statistics from 2022 and 2023, has settled on specific operational parameters for automated change-point event detection at each station. For AXID01, the adopted configuration uses a Z-score detection threshold of 3.5 standard deviations above the background distribution of the detrended time series, computed using the robust median-based estimator described in Section 9. This threshold was selected to achieve a false-alarm rate below 2% per year while maintaining sensitivity to slow-slip events with pressure amplitudes down to approximately 0.02 kPa, which corresponds to a vertical seafloor displacement of roughly 2 millimeters using the standard network conversion factor.

The minimum sustained duration required for an anomalous window to be promoted from a raw detection candidate to an accepted event catalog entry is 2.0 hours at AXID01. Events lasting fewer than 2 hours — even if they exceed the Z-score threshold — are classified as sub-threshold transients and are logged separately but not included in the slow-slip event catalog. The rationale for this duration criterion is that the slow tectonic processes targeted by the PSON network (episodic tremor and slip, shallow creep on the ridge-bounding faults) evolve on timescales of hours to days, and sub-2-hour pressure transients at this site are more likely to be oceanographic in origin or attributable to the instrument artifacts described above.

### 2.6 Operational History and Notable Events

Since its July 2021 deployment, AXID01 has recorded continuous data through five distinct geophysical event sequences. The most significant was a volcano-tectonic earthquake swarm in October 2022 associated with a deep intrusion beneath the Axial caldera; this produced a deflation signal visible in both the pressure and tilt channels over a period of approximately 18 hours. The event was detected by the automated pipeline as a slow-slip candidate and was subsequently confirmed through corroboration with the OOI seismograph network and real-time tremor detection performed by Dr. William Wilcock's group at the University of Washington.

More recently, a series of small pressure anomalies observed during the summer of 2023 were investigated as potential slow-slip precursors. Most were ultimately attributed to episodic changes in the strength of the Cascadia deep-water current that advects cold bottom water northward across the caldera, producing pressure changes of up to 0.05 kPa over periods of 12–24 hours. The detrending algorithm in the standard pipeline removes much of this signal if the trend is computed over a sufficiently long window (minimum 7 days), but shorter trend windows can leave residuals that occasionally exceed the detection threshold. The PSON data management group recommends using a 10-day detrending window for routine analysis of AXID01 data to minimize these oceanographic contamination events.

No major data outages, sensor failures, or calibration anomalies have been recorded at AXID01 since the September 2023 servicing cruise.

---

## 3. Station AXID02 — Axial Seamount Secondary Monitoring Array

### 3.1 Location, Deployment, and Physical Setting

Station AXID02 provides a second independent pressure measurement on the Axial Seamount caldera floor, sited at 45.9531° N, 130.0094° W at a depth of 4162 meters, approximately 180 meters south-southwest of AXID01. The two-station configuration was motivated by the need to distinguish localized instrument effects or lander disturbances from true geophysical ground deformation: an event that appears coherently in both channels is far more likely to represent a genuine pressure anomaly than an event that appears in only one.

AXID02 was deployed two days after AXID01, on July 17, 2021, using the same vessel and ROV. The lander design is identical to AXID01 — same tripod frame, same Paroscientific transducer model, same acoustic modem configuration — which facilitates direct comparison between stations. The primary difference in the deployment is the substrate: AXID02 rests on a thin veneer of seafloor sediment rather than exposed basalt, meaning that the frame anchoring uses helical screw anchors rather than the epoxy bolts used at AXID01. Visual inspection during the September 2023 servicing dive confirmed that the screw anchors had not shifted measurably since deployment.

The tiltmeter at AXID02 is the same model as at AXID01 (Applied Geomechanics 702-2G-C) but is body-frame-tilted at −1.8° from vertical, a consequence of slight irregularity in the sediment surface at the precise landing point. This tilt is a static offset in the tilt channel and does not affect the pressure measurement.

### 3.2 Secondary Calibration Coefficients

The September 2023 calibration intercomparison at AXID02 used the same SBE 37-SM MicroCAT reference instrument as at AXID01, which was shuttled between the two station sites during a single 24-hour ROV operations window. Analysis of the intercomparison data by instrument technician Margaret Holt, with cross-check by postdoctoral researcher Dr. Sofia Petrov, yielded calibration coefficients slightly different from those at AXID01, reflecting genuine differences in crystal age and prior thermal history between the two Paroscientific units.

At AXID02, the pressure gain correction factor is 0.9891. This value is less than unity, indicating that the raw sensor output at AXID02 slightly overstates absolute pressure relative to the reference: the gain adjustment scales the raw reading downward by approximately 1.1%. The additive offset for AXID02 is +0.072 kilopascals, meaning the raw signal requires a small upward correction at the zero point. These coefficients apply in the same formula as at all other PSON stations: calibrated_pressure_kPa = raw_value × 0.9891 + 0.072. The calibrated baseline pressure of AXID02 is approximately 416 kPa.

The origin of the sub-unity gain at AXID02 was investigated and is attributed to the slightly different resonator temperature experienced by this unit's crystal relative to the temperature modeled in the factory calibration. The Axial caldera floor temperature at AXID02's site, at 1.79°C, is marginally colder than at the AXID01 site (1.82°C), and the difference in crystal behavior between the two units at these temperatures is consistent with the observed gain discrepancy.

### 3.3 Signal Quality and Detection Parameters

The noise characteristics of AXID02 are very similar to those of AXID01, with background root-mean-square detrended pressure noise of 0.004–0.006 kPa in the 10-minute record. This similarity is expected given the nearly identical instrument design, colocation within the same oceanographic environment, and comparable deployment depths.

The adopted Z-score detection threshold for AXID02 is 3.5 standard deviations — the same as at AXID01 — reflecting the two stations' similar noise environments and the goal of maintaining a coherent detection capability for events that might produce signals at both Axial stations simultaneously. Events that trigger at AXID01 and AXID02 within a 30-minute window of each other are flagged for cross-station coherence analysis, which substantially increases confidence in slow-slip attribution over single-station triggers.

The minimum duration criterion at AXID02 is 2.0 hours, matching AXID01. This value was arrived at by examining the duration distribution of historical triggers and identifying the threshold below which the trigger rate became dominated by instrument artifacts rather than plausible geophysical events. Events lasting 2 hours or more account for approximately 85% of the triggers that ultimately survive human expert review, whereas sub-2-hour triggers have a false-positive rate exceeding 60% when manually inspected.

### 3.4 Operational History

AXID02 has been operating continuously with high data completeness since its July 2021 deployment. The instrument experienced one data gap of approximately 6 hours in March 2023 during a severe storm event that disrupted the acoustic modem communication; the gap is flagged in the database with a quality note but does not affect surrounding data quality. The September 2023 servicing dive repaired a minor corrosion issue on the modem antenna bracket and cleaned the pressure port screen.

A notable event in AXID02's record occurred in February 2023 when a small seismic sequence beneath the caldera produced a short-duration (approximately 4 hours) pressure perturbation visible at both Axial stations. Analysis suggested a shallow fault rupture within the caldera floor at a depth consistent with the brittle-ductile transition beneath Axial's magma reservoir. The event was documented in a conference abstract by the OOI science team but has not yet been published in a peer-reviewed journal.

---

## 4. Station NEMO01 — Northern Extension Monitor Station

### 4.1 Location, Deployment, and Physical Setting

Station NEMO01 serves as the northern anchor of the PSON array, deployed at 47.1203° N, 128.8847° W at a depth of 3822 meters on the upper continental slope southwest of the Juan de Fuca Plate's eastern margin. The station was installed in September 2020 — the earliest deployment in the current network configuration — following a successful pilot study using autonomous floats that demonstrated elevated low-frequency pressure variability in the region attributable to shallow episodic slow-slip events on the upper Cascadia megathrust.

The NEMO01 site occupies a relatively flat sediment-covered terrace on the slope, where the Pleistocene and Holocene sediment drape is approximately 3–5 meters thick. The lander is stabilized by a weighted base plate rather than borehole anchors, relying on sediment friction for stability. Visual inspections during two ROV servicing dives (August 2021 and September 2023) have confirmed that the base plate has not shifted measurably. The surrounding sediment shows evidence of bottom current-driven ripple migration, but these sediment transport processes are too slow to affect the instrument on the timescale of individual event detection.

The depth of 3822 meters places NEMO01 shallower than the two Axial stations, which has implications for the calibrated pressure baseline and for the dominant oceanographic noise sources at the site. The station sits closer to the oxygen minimum zone and the depth range where mesoscale eddy-induced pressure variability is more pronounced in the northeast Pacific. This elevated oceanographic noise drives the station's higher Z-score detection threshold relative to the Axial sites.

### 4.2 Secondary Calibration Coefficients

The secondary calibration of NEMO01 was performed in September 2023, when the same SBE 37-SM MicroCAT reference instrument used at the Axial stations was lowered to NEMO01's deployment site via CTD rosette cast from the surface ship. The intercomparison lasted approximately 14 hours, during which both instruments collected measurements at 1-minute intervals. The data were analyzed by senior research associate Dr. Claire Morrison of Oregon State University's College of Earth, Ocean, and Atmospheric Sciences.

The calibration analysis revealed a gain correction factor of 1.12 for NEMO01's pressure channel. This is a substantially larger correction than at either Axial station, and it reflects the older age of the Paroscientific transducer deployed here — this unit, serial number 138742, was purchased and factory-calibrated in 2017, making it approximately three years older than the Axial units at the time of the September 2023 intercomparison. Long-term resonator frequency drift in aging crystals is a well-documented phenomenon in Paroscientific instruments, and the 12% scale deviation observed at NEMO01 is within the expected range for a six-year-old unit that has been continuously operating at depth. The instrument remains within Paroscientific's repair-and-recalibration specification and has been recommended for factory recalibration during the next scheduled servicing window, tentatively planned for summer 2025.

The additive pressure offset for NEMO01 is +0.380 kilopascals, the largest zero-point correction among the current active PSON stations. This offset arises partly from the resonator drift noted above and partly from a small but confirmed thermal gradient between the pressure port and the reference CTD probe during the intercomparison, attributable to slight differences in the thermal equilibration time of the two instruments after lowering from the surface. The intercomparison design was adjusted to account for this by extending the equilibration wait time to 90 minutes before the comparison period commenced, and Dr. Morrison's analysis confirms that the thermal correction is well characterized.

The calibration formula for NEMO01 is: calibrated_pressure_kPa = raw_value × 1.12 + 0.380. The calibrated baseline pressure for this station is approximately 382 kPa, consistent with a depth of roughly 3820 meters.

### 4.3 Signal Quality, Noise Characteristics, and Oceanographic Context

NEMO01 sits in a more energetic oceanographic environment than the Axial stations, which manifests as elevated broad-band pressure variance in the 10-minute averaged data. Background root-mean-square detrended pressure noise at NEMO01 is typically 0.006–0.010 kPa, compared to 0.004–0.006 kPa at the Axial array. The additional noise originates from several sources: mesoscale eddies transiting the region contribute pressure anomalies of 0.05–0.2 kPa over periods of days to weeks that require careful detrending, deep current variability associated with the California Undercurrent contributes higher-frequency variability on timescales of hours, and occasional deep-sea storm pulses from major Northeast Pacific cyclones produce pressure increases of up to 0.05 kPa on timescales of 12–48 hours.

Despite this elevated background, NEMO01 captures scientifically important slow-slip events because the station is ideally placed to detect pressure anomalies from episodic creep episodes on the upper Cascadia megathrust, where slow-slip events produce vertical displacements of 5–20 millimeters at the seafloor over durations of days to weeks. At the network's standard conversion factor of 0.1 meters per kilopascal, these displacements correspond to pressure anomalies of 0.05–0.20 kPa — well above the detection threshold for NEMO01 even given its elevated noise floor.

The primary cause of false detections at NEMO01 in prior analysis runs has been the imperfect removal of mesoscale eddy pressure signals by the detrending step. Using a 10-day linear detrend window, as recommended in Section 9, typically removes the eddy contribution adequately, but during periods when multiple eddies pass through the region in rapid succession, the residual after detrending can contain elevated variance that triggers the automated detector. This is the principal motivation for NEMO01's higher Z-score threshold relative to the Axial stations.

### 4.4 Event Detection Parameters

After extensive review of the NEMO01 detection performance record from 2021 through 2023, the PSON analysis team has established a Z-score threshold of 4.0 standard deviations for this station. At this threshold, the automated detector achieves a false-alarm rate comparable to the Axial stations (below 3% per year) despite NEMO01's higher background noise, because the threshold scales with the noise level in a relative sense.

The minimum duration requirement for NEMO01 is 3.0 hours — longer than the 2.0-hour threshold used at the Axial stations. The extended duration criterion reflects two considerations. First, the oceanographic noise sources at NEMO01 tend to produce pressure transients of 1–3 hours duration that closely resemble tectonic slow-slip signals in their amplitude characteristics. By requiring 3 hours of sustained anomalous pressure, the detection criterion is tailored to preferentially capture the broader classes of tectonic and volcanic slow-slip events while rejecting the majority of oceanographic noise events. Second, the slow-slip events that NEMO01 is scientifically tasked with detecting along the upper Cascadia megathrust are expected, based on geodetic and seismic evidence, to produce seafloor signals lasting at least 3–6 hours, so the duration criterion does not significantly degrade the scientific recovery rate for genuine events.

### 4.5 Operational History

NEMO01 began accumulating its continuous time series in September 2020 and has provided data through multiple notable geophysical episodes since then. The most scientifically significant of these was a sequence of slow-slip events on the upper Cascadia megathrust detected in November 2022 that correlated with elevated tremor rates observed on shore-based seismic networks. The PSON team reported these events at the 2023 AGU Fall Meeting, and a manuscript describing the joint geodetic and pressure analysis is in review at Earth and Planetary Science Letters.

Minor operational issues at NEMO01 include two instances of data gaps from acoustic modem communication loss: a 9-hour gap in January 2021 during the early operational period and a 3-hour gap in June 2022 following a modem firmware update that required a manual reset. Both gaps are documented in the database quality flags.

The September 2023 servicing dive replaced the battery pack at NEMO01 — the original pack had been in service since the station's deployment three years earlier — and performed a post-replacement pressure intercomparison that confirmed the calibration coefficients documented in Section 4.2. The dive report notes that minor benthic organism growth was found on the pressure port screen, consistent with the seasonal fouling pattern observed at AXID01, and the screen was cleaned.

---

## 5. Station NEMO02 — Northern Extension Secondary Station (Standby)

### 5.1 Status Note

Station NEMO02 was placed in standby mode following the discovery of water ingress in the junction box housing during an October 2023 visual inspection via autonomous underwater vehicle (AUV). The flooding affected the main communication electronics board, rendering the acoustic modem inoperable. The pressure and temperature sensors themselves showed no sign of damage, and the data stored in the onboard memory card up to the time of the flooding incident were successfully recovered via ROV extraction during a dedicated recovery dive in November 2023.

NEMO02 is not included in the active calibration tables for the January 2024 revision of this dossier. The PSON operations committee has authorized a repair and redeployment attempt during the planned 2025 servicing cruise, subject to availability of a replacement junction box assembly. Historical data from NEMO02 (September 2020 through early October 2023) are fully archived and accessible through the data portal.

### 5.2 Historical Calibration Summary

For reference purposes, the secondary calibration coefficients determined for NEMO02 during the August 2021 intercomparison were: pressure gain of 0.9973 and pressure offset of +0.144 kilopascals. The detection threshold used in the historical catalog for NEMO02 was 4.0 standard deviations with a minimum duration of 3.0 hours, matching NEMO01. These values are preserved in the historical catalog documentation but should not be applied to new data analysis until the station is redeployed and recalibrated.

The geographic position of NEMO02 was 47.2891° N, 128.7204° W at a depth of 3694 meters, approximately 195 kilometers northeast of NEMO01 and positioned to provide tighter triangulation on slow-slip source regions along the upper Cascadia margin. Loss of this station reduces the array's spatial resolution for slow-slip event location but does not eliminate the capability for detection.

---

## 6. Station JUAN01 — Juan de Fuca Ridge Vent Field Station

### 6.1 Location, Deployment, and Physical Setting

Station JUAN01 is deployed on the Juan de Fuca Ridge crest at 47.9667° N, 129.1083° W at a depth of 2318 meters, making it the shallowest station in the active PSON network. The Juan de Fuca Ridge at this latitude is a fast-spreading mid-ocean ridge system (full spreading rate approximately 60 mm per year), and the vent field environment presents unique observational challenges. Hydrothermal fluid circulation at and near the ridge axis produces temperature anomalies that, while small at the ambient seafloor conditions outside the active vent fields, introduce thermally driven pressure variations into the sensor record that must be carefully characterized.

The station was originally deployed in April 2019 as part of a separate NSF-funded study of hydrothermal plume dynamics, predating the formal PSON network structure. It was folded into the PSON array in 2021 when the consortium recognized the value of having a ridge-crest pressure monitor for detecting fault creep and volcanic inflation events along the ridge axis. Instrument upgrades performed during a July 2021 ROV dive replaced the original pressure gauge (which was reaching end-of-life) with a new Paroscientific 8B7000-I unit and upgraded the telemetry system to include both acoustic modem and Iridium satellite capabilities.

The physical setting of JUAN01 is more complex than the sediment-covered slope environments of NEMO01 and the caldera floor of AXID01/02. The lander sits on a small basalt platform within a depression approximately 30 meters across, surrounded by faulted ridge-crest terrain and within 400 meters of two active black smoker chimney clusters. The proximity to hydrothermal vents is scientifically valuable but operationally demanding: the hydrothermal plumes create localized pressure gradients within the basin, and the thermal noise in the pressure channel is correspondingly higher than at the calmer Axial caldera sites.

### 6.2 Secondary Calibration Coefficients

The September 2023 servicing and calibration cruise also included a CTD cast to the JUAN01 site, using the same SBE 37-SM MicroCAT reference instrument. Because JUAN01 is the most challenging access point in the array — it requires the ship to transit approximately 90 nautical miles from the COAX01 site — the intercomparison duration was limited to 11 hours due to weather constraints. Analysis of the shortened intercomparison was performed by senior instrument technician Margaret Holt under review by PSON principal investigator Dr. James DeVries.

The resulting calibration coefficients for JUAN01's pressure channel are a gain of 1.0089 and an offset of +0.108 kilopascals. These values indicate modest corrections: the gain correction of approximately 0.9% suggests that this transducer (deployed and calibrated in 2021, younger than NEMO01's instrument) exhibits less crystal drift, and the positive offset of 0.108 kPa is consistent with minor zero-point instability in the thermal environment near the ridge crest. The formula applied is: calibrated_pressure_kPa = raw_value × 1.0089 + 0.108. The calibrated baseline pressure for JUAN01 is approximately 231 kPa, consistent with its depth of roughly 2318 meters.

### 6.3 Signal Quality and Known Noise Sources

JUAN01 has the most complex pressure noise environment in the PSON array because of the multiple distinct physical processes that produce pressure variability at the ridge-crest site. Beyond the standard oceanographic background signals (tidal loading, mesoscale eddies, internal waves), the hydrothermal environment contributes short-duration pressure transients attributed to the following mechanisms:

The most common source of elevated pressure noise is episodic recharge of the sub-seafloor hydrothermal system. Observations at other ridge-crest monitoring sites have documented brief pressure pulses of 0.01–0.05 kPa lasting 20–60 minutes that are thought to arise from boiling at depth within the hydrothermal upflow zone and the associated changes in fluid density. These events are too brief to survive JUAN01's minimum-duration criterion under normal operations, but during periods of elevated hydrothermal activity (e.g., following small seismic swarms) they can cluster in time and produce composite signals that are longer-lived.

The second notable noise source is what the PSON team has labeled "thermal backflow events" — episodes lasting 2–6 hours during which the local bottom current reverses direction and drives warmer, lighter hydrothermal plume water over the JUAN01 lander site. These events produce a slow decrease in measured pressure of approximately 0.01–0.03 kPa as the water column above the sensor becomes less dense. Unlike most pressure anomalies at this site, thermal backflow events are correlated with simultaneous temperature excursions in the temperature sensor channel and can therefore be identified and flagged through joint pressure-temperature analysis.

### 6.4 Event Detection Parameters

Given the elevated noise environment at JUAN01, the event detection parameters for this station differ significantly from the other PSON sites. After thorough review of three years of operational data and collaboration with the hydrothermal science team, the PSON analysis group established a Z-score detection threshold of 3.0 standard deviations for JUAN01. This threshold, lower than at any other active PSON station, reflects the tighter coupling between tectonic slow-slip signals and nearby noise sources at this site: using a higher threshold would eliminate many events of scientific interest that occur at the ridge crest with amplitudes just above the noise floor.

The minimum duration criterion is 1.5 hours for JUAN01, compared to 2.0 hours at the Axial stations and 3.0 hours at NEMO01. The shorter minimum duration reflects two considerations. First, ridge-axis tectonic and volcanic events at the Juan de Fuca spreading center can evolve on shorter timescales than subduction zone slow-slip events detectable at NEMO01, with some ridge deflation episodes completing over 1–2 hours. Second, the station's catalog is subjected to a more intensive post-detection screening step involving cross-referencing with the OOI seismic catalog and the NEPTUNE Canada hydrophone array to discriminate tectonic events from hydrothermal noise, which compensates for the lower threshold by providing an additional quality gate downstream.

### 6.5 Planned Maintenance: January 2024

JUAN01 is scheduled for a battery replacement and sensor array realignment during a planned ROV servicing window in January 2024. The current battery pack, installed during the July 2021 upgrade, is approaching the end of its expected service life, and voltage telemetry indicates a decline consistent with depletion of approximately 85% of total capacity. The battery replacement is mandatory to prevent data loss from power failure.

Additionally, post-deployment analysis of the tiltmeter orientation at JUAN01 — which was added during the 2021 upgrade — indicates that the instrument body frame has drifted approximately 2.3° from its intended orientation, possibly due to sediment creep on the sloped basalt substrate. The reorientation procedure requires physical manipulation of the lander by the ROV manipulator arm, which will necessitate a brief shutdown of the pressure data acquisition system.

The planned maintenance window spans January 8 through January 12, 2024. All automated catalog algorithms and event detection pipelines analyzing JUAN01 data from this period should exclude the maintenance window from detection consideration: pressure readings during the January 8–12, 2024 maintenance period are subject to operational disturbances from ROV proximity, instrument manipulation, and acoustic emissions from the ROV thrusters, and any apparent pressure events detected during this window should be attributed to maintenance activity rather than geophysical causes. Events that begin before January 8 or end after January 12 remain valid for analysis, provided the anomalous portion does not overlap with the maintenance window.

### 6.6 Operational History and Notable Events

JUAN01's long operational history since 2019 (with the instrument upgrade in 2021) provides a valuable multi-year context for interpreting current data. Notable geophysical episodes captured by JUAN01 include:

A seismic swarm in July 2019 associated with a minor eruptive episode on the ridge crest, which produced a deflation event in the pressure record lasting approximately 14 hours with a peak amplitude of 0.3 kPa. This event was also detected by the OOI hydrophone array and is documented in a 2020 paper in Geophysical Research Letters by Dziak et al.

A series of slow-slip events in March 2022 that produced pressure anomalies at JUAN01 of 0.15–0.25 kPa each, lasting 4–8 hours, and that correlated with elevated acoustic emission rates on the OOI hydrophone network. These events were interpreted as shallow fault creep on the eastern limb of the Juan de Fuca Ridge transform fault system.

The August 2023 seismic swarm previously mentioned in the executive summary, during which intermittent communication loss created a 14-hour gap in the continuous record. The swarm itself, which preceded the gap, produced visible pressure perturbations that have been flagged as potential post-main-shock slow-slip candidates by the analysis team. Investigation is ongoing.

---

## 7. Station COAX01 — Cascadia Basin Deep-Sea Outpost

### 7.1 Location, Deployment, and Physical Setting

Station COAX01 occupies the geographically most remote position in the active PSON array, located at 46.2185° N, 129.7294° W at a water depth of 4831 meters — the deepest station in the network. The Cascadia Basin in the vicinity of COAX01 is an abyssal plain environment dominated by fine sediment (siliceous and carbonate ooze) that has accumulated over millions of years of pelagic sedimentation. Unlike the ridge-crest or slope environments of the other PSON stations, the COAX01 site sits on essentially flat, geologically quiescent seafloor with no known volcanic or tectonic structures within 20 kilometers.

The station was deployed in March 2022 to extend the network's aperture toward the trench axis and to improve the constraint on the spatial distribution of deep slow-slip events that may originate near the décollement beneath the thick sediment prism of the accretionary wedge. COAX01's position, on the subducting plate to the west of the accretionary wedge toe, provides a fundamentally different observational geometry relative to NEMO01 and JUAN01, both of which are on or near the overlying plate.

Because COAX01 is the only PSON station connected by fiber-optic cable to shore, it provides near-real-time data transmission with latency below 5 seconds, compared to the daily acoustic modem data bursts at the other stations. This capability has been particularly valuable for studying fast transient events but is underutilized for the present slow-slip catalog because the temporal resolution of the catalog analysis is bounded by the 10-minute sampling interval.

The deep abyssal plain environment at COAX01 is among the most energetic in the network from an oceanographic pressure variability standpoint. The abyssal Pacific receives pressure signals from passing deep-water eddies originating in the Antarctic Bottom Water circulation system, from deep Pacific tidal harmonics, and from the very low-frequency end of the deep-ocean barotropic pressure spectrum. These signals are responsible for COAX01 having the highest background pressure noise in the PSON array.

### 7.2 Secondary Calibration Coefficients

The calibration of COAX01 was performed during a separate servicing expedition in June 2023, six months ahead of the main September 2023 PSON cruise, because the fiber cable connection to COAX01 had been suffering intermittent noise issues that the operations team attributed to a possible degradation of the calibration coefficients. A ship-lowered SBE 37-IM MicroCAT CTD (deep-rated version for the 4831-meter depth requirement; the standard SBE 37-SM does not carry depth certification beyond 4500 meters) was used as the reference instrument for a 20-hour intercomparison.

Analysis of the intercomparison data, conducted by Dr. Yuki Tanabe in June 2023 and verified by PSON instrument specialist Dr. Marco Fontaine in August 2023, established a pressure gain correction factor of 0.9944 for COAX01. This slightly sub-unity gain is the smallest correction in the active network and reflects the relatively recent factory calibration of this instrument (2022, just prior to deployment) combined with the extreme stability of the ultra-deep pressure environment, which keeps the transducer at near-constant temperature and pressure and minimizes resonator drift. The additive pressure offset for COAX01 is −0.156 kilopascals, a modest negative correction attributable to a small systematic bias in the zero-point reading identified during the intercomparison analysis. 

The calibration formula for COAX01 is: calibrated_pressure_kPa = raw_value × 0.9944 + (−0.156). The calibrated baseline pressure is approximately 483 kPa, consistent with a depth of approximately 4830 meters.

Note for historical users: earlier versions of this dossier (Revisions 7.2 and 7.3) contained a typographical error in the COAX01 gain coefficient, reporting it as 0.9994 rather than the correct 0.9944. The error was identified by Dr. Tanabe in December 2023 during her independent audit of the calibration records. All catalog entries and publications using COAX01 calibrated data prior to January 2024 should be reviewed against the corrected gain value. The difference — 0.005 — is small enough that most published event magnitude estimates are within the uncertainty budget, but users performing precision comparisons should apply the correction.

### 7.3 Signal Quality and Noise Characteristics

As noted above, COAX01 has the highest background pressure noise in the network, with root-mean-square detrended values of 0.010–0.018 kPa in the 10-minute averaged data under typical oceanographic conditions. During periods of strong Antarctic Bottom Water intrusion events, background noise can temporarily reach 0.025 kPa or higher for periods of several days. These elevated-noise periods are flagged in the database quality log and should be treated with caution in any automated detection pipeline.

Additionally, COAX01 is positioned near a submarine telecom cable corridor, and occasional cable ship activity in the broader region (although no cable passes directly overhead) has been associated on two occasions with anomalous acoustic energy in the water column that produced brief pressure spikes in the COAX01 record. These events are identified by their very short duration (single-sample spikes) and are filtered out by the minimum-duration criterion.

The fiber cable connection itself can introduce very low-level electrical noise into the pressure measurement electronics if there is a leakage path from the cable's power transmission system. The COAX01 engineering team monitors this potential interference source using a shielding monitor channel; as of the most recent inspection in November 2023, no anomalous electrical noise injection has been detected.

### 7.4 Event Detection Parameters

Given COAX01's substantially elevated noise environment compared to the other PSON stations, the event detection parameters are the most conservative in the network. The adopted Z-score detection threshold for COAX01 is 5.0 standard deviations. This high threshold is necessary to prevent the automated catalog from being overwhelmed by oceanographic noise triggers in the abyssal plain environment while still maintaining sensitivity to genuine tectonic signals.

At a threshold of 5.0 standard deviations, the expected false-alarm rate from purely Gaussian noise is approximately 1 in 3.5 million samples, which translates to well under one false alarm per year in the 52,704-sample annual record. In practice, the actual false-alarm rate is slightly higher because the deep-ocean pressure noise is not perfectly Gaussian and has heavier tails than a normal distribution, but the adopted threshold has been effective in keeping the COAX01 catalog manageable at the cost of some sensitivity to smaller events.

The minimum duration criterion for COAX01 is 4.0 hours. This extended minimum duration reflects two factors: the elevated noise causes occasional noise bursts that can sustain elevated Z-scores for 1–3 hours without representing genuine tectonic events, and the slow-slip events expected to be detectable at this site — deep slow-slip events propagating outward from the Cascadia megathrust décollement — are modeled to produce pressure signals lasting 6 hours or more at the COAX01 location. A 4-hour minimum duration therefore selects for the class of signals most likely to represent genuine deep-subduction events.

### 7.5 Operational History

COAX01 has been operating since March 2022. In its approximately 22 months of operation to the time of this dossier's preparation, it has not recorded any clearly confirmed tectonic slow-slip events, which is consistent with the station's role as a new array element still building its detection record. Two candidate events were identified in the provisional catalog in late 2022 — one in September and one in November — but both were subsequently attributed to major Antarctic Bottom Water intrusion events based on temperature-pressure correlation analysis and comparison with deep current meter data from a nearby WHYCOS mooring.

The calibration correction described in Section 7.2, combined with the prior typographical error in the gain coefficient that persisted through two dossier revisions, means that any COAX01-based geophysical analyses published before January 2024 should be reviewed for magnitude accuracy. The PSON data management group is preparing a technical note documenting the correction and its implications, which will be circulated to all active COAX01 data users.

---

## 8. Station NEMO02 — Extended Notes (Historical)

Station NEMO02 accumulated three years of data from September 2020 through early October 2023 that remains scientifically valuable for the study of slow-slip event patterns on the upper Cascadia margin. The full historical record is described in the PSON data archive documentation and will not be repeated here. The key operational parameters that governed its detection pipeline during its operational period are preserved in this section for reference.

The station operated with a Z-score threshold of 4.0 standard deviations, matching NEMO01. Its minimum duration requirement was 3.0 hours, also matching NEMO01. The two NEMO stations were designed as a complementary pair, and their detection parameters were deliberately aligned to allow direct comparison of event catalogs. Several slow-slip events that triggered at NEMO01 during the 2021–2023 operational period produced coherent signals at NEMO02, providing triangulation on source positions.

NEMO02 deployed a Paroscientific 8B7000-I unit, serial number 135891, which was among the older instruments in the PSON inventory at the time of deployment. Regular comparison with NEMO01 data and the August 2021 reference CTD intercomparison confirmed the calibration coefficients remained stable throughout the operational period. Replacement of this unit is planned for the next NEMO02 redeployment, as the age of the crystal resonator now warrants factory recalibration.

---

## 9. Signal Processing Protocols

### 9.1 Overview of the Standard Detection Pipeline

This section describes in detail the four-stage detection pipeline used to convert raw PSON database pressure readings into a vetted slow-slip event catalog. All analyses using PSON data for event catalog construction should follow these protocols to ensure consistency with the archived event database maintained by the PSON data management group. Deviations from these protocols, such as using different detrending windows or different Z-score estimators, should be clearly documented in any publication using PSON data.

The four stages are: secondary calibration, detrending, robust Z-score computation, and Bayesian change-point scoring. Each stage is described in its own subsection below.

### 9.2 Stage 1: Secondary Calibration

The first stage of the pipeline applies the station-specific secondary calibration coefficients to convert the raw_value column in the database to calibrated pressure in kilopascals. The calibration formula is:

calibrated_pressure = raw_value × gain + offset

where gain and offset are the station-specific constants documented in Sections 2 through 7 of this dossier. This operation is applied to every pressure sample in the time series before any further processing. The gain correction is applied first (multiplicative) and the offset is added second (additive), consistent with the linear calibration model derived from the intercomparison measurements. No other transformations are applied during this stage.

Analysts should ensure that they are applying the correct calibration coefficients for the specific station being analyzed and that they are using the most current dossier revision. Using calibration coefficients from a superseded revision (particularly for COAX01, where a typographical error existed in Revisions 7.2 and 7.3) will produce systematically biased calibrated series.

### 9.3 Stage 2: Detrending

The detrending step removes the long-period background signal from the calibrated pressure time series to isolate anomalies associated with slow geophysical events. The dominant long-period background signals are: (a) oceanographic tidal loading, which contributes pressure variations of up to 2 kPa peak-to-peak at diurnal and semi-diurnal periods; (b) the very slow secular pressure change associated with long-term changes in the ocean's thermohaline state; (c) the slow instrument drift characterized in the monthly calibration checks; and (d) mesoscale oceanographic variability at periods of days to weeks.

The standard detrending approach used by the PSON analysis team is a least-squares polynomial fit of degree 2 (quadratic trend) to a rolling 10-day window centered on the time point of interest, with the fitted quadratic subtracted from the calibrated series at that time point. The 10-day window was selected based on empirical tests that showed it effectively removes tidal and mesoscale oceanographic trends while preserving the anomalous signals associated with slow-slip events, which typically evolve on timescales of hours.

For time series processing implementations that use a segment-by-segment approach rather than a rolling window, it is acceptable to use a linear (degree 1) polynomial fit over a 7–14 day segment, provided that segment boundaries are not placed within known or candidate event periods. The quadratic rolling window approach is preferred for production catalog work, but the linear segment approach may be sufficient for rapid exploratory analysis.

Detrending should be applied only to pressure readings with no quality flag set in the database. Segments containing flagged readings (e.g., modem transmission artifacts or known maintenance periods) should be excluded from the detrend window computation and gap-filled with the local trend value before computing Z-scores. The detrended time series should have approximately zero mean and a standard deviation in the range of 0.004–0.015 kPa depending on station and season, as described in the station-specific noise characterization sections.

### 9.4 Stage 3: Robust Z-Score Computation

Following detrending, the pipeline computes a robust Z-score for each sample using the median absolute deviation (MAD) as the dispersion estimator rather than the sample standard deviation. The choice of a robust estimator is critical for slow-slip event detection because the presence of the events themselves elevates the tails of the pressure distribution beyond what would be expected from Gaussian noise alone. Using the sample standard deviation as the dispersion estimator would inflate the noise estimate and reduce detection sensitivity; the MAD, being insensitive to values more than roughly half a standard deviation from the median, provides a stable characterization of the background noise floor even in the presence of anomalous events.

The Z-score for sample i is computed as:

Z_i = (x_i − median(x)) / (1.4826 × MAD(x))

where x is the full detrended time series for the station and sensor type, median(x) is the sample median, MAD(x) = median(|x_j − median(x)|) is the median absolute deviation of the series, and the factor 1.4826 is the consistency constant that makes the denominator a consistent estimator of the standard deviation for normally distributed data. The resulting Z-score series has the property that values near zero represent the typical background, while large positive or negative values indicate anomalies relative to the background distribution.

The computation of median and MAD should be performed on the full available time series for the analysis window (typically one month of data, as in the January 2024 dataset), not on rolling short windows. Computing these statistics on short windows would cause the denominator to change over time as events enter and exit the window, which can create edge effects and spurious changes in Z-score level near event boundaries.

### 9.5 Stage 4: Bayesian Change-Point Scoring

The final stage of the detection pipeline assigns a confidence score to each candidate event window identified by the Z-score threshold criterion. The Bayesian change-point scoring approach computes a log Bayes factor comparing two hypotheses for a candidate window of duration W centered on the window's peak Z-score:

Hypothesis H0 (no event): the pressure in the window is drawn from the background Gaussian distribution characterized by the MAD-based standard deviation estimate.

Hypothesis H1 (event): the pressure in the window represents a genuine sustained anomaly; the mean of the distribution within the window is displaced from zero by an amount delta, where delta is the mean detrended pressure in the candidate window.

The log Bayes factor log_BF = log P(data | H1) − log P(data | H0) is approximated as:

log_BF ≈ (n × delta^2) / (2 × sigma_background^2) − (1/2) × log(n)

where n is the number of samples in the candidate window, delta is the mean detrended pressure in the window (equivalent to the mean calibrated anomaly), and sigma_background is the background standard deviation estimated from the MAD. The second term is a penalty for the model complexity (one free parameter, delta) under the Bayesian information criterion approximation.

The confidence score assigned to the event is a sigmoid transformation of the log Bayes factor:

confidence_score = 1 / (1 + exp(−log_BF / scale_factor))

where scale_factor = 2.0 is a tuning parameter that maps log Bayes factors of typical magnitude (5–20) to confidence scores in the range 0.5–0.99. Confidence scores below 0.5 indicate that the data marginally favor the no-event hypothesis (or that the evidence is ambiguous), and confidence scores above 0.7 indicate strong evidence for a genuine event. All events in the PSON catalog are reported with their confidence scores regardless of magnitude, allowing downstream users to impose their own confidence cutoffs.

### 9.6 Displacement Estimation

The estimated vertical seafloor displacement associated with each detected pressure anomaly is computed from the mean calibrated pressure anomaly over the event duration using the standard PSON conversion factor. For all PSON stations operating in the depth range of 2000–5500 meters, the conversion factor between sustained calibrated pressure anomaly and vertical seafloor displacement has been standardized at 0.1 meters per kilopascal. This value is derived from the local seawater density (approximately 1027–1029 kg/m³ at PSON station depths) and the standard gravitational acceleration:

displacement_meters = mean_anomaly_kPa × 0.1

where mean_anomaly_kPa is the mean detrended calibrated pressure in the candidate event window. Positive mean anomaly corresponds to upward seafloor displacement (compression of the water column above the sensor), and negative mean anomaly corresponds to downward displacement (extension or subsidence).

The uncertainty on the displacement estimate is dominated by the uncertainty in the mean pressure anomaly over the event window, which scales as sigma_background / sqrt(n_samples). For typical event windows of 12–36 samples (2–6 hours at 10-minute intervals) and typical background standard deviations of 0.005–0.010 kPa, the displacement uncertainty is approximately 0.001–0.003 meters (1–3 millimeters).

### 9.7 Exclusion Criteria and Quality Flags

Events that are detected by the automated pipeline but fall within known data-quality exclusion windows should be flagged as excluded rather than deleted from the catalog output. The catalog output format includes both an `excluded` boolean field and an `exclusion_reason` string field, allowing downstream users to understand why specific events were not accepted into the active catalog while preserving a complete record of all pipeline outputs.

Current exclusion criteria include: (1) maintenance windows during which known ROV operations or instrument interventions were taking place (see individual station sections for dates); (2) periods flagged in the database quality log as containing known instrument artifacts; (3) time windows covering significant data gaps (>15 samples missing within a 3-hour window) that degrade the detrending and Z-score computation quality; and (4) any window where the associated temperature sensor shows a thermal anomaly exceeding 0.05°C simultaneously with the pressure anomaly, which is diagnostic of a hydrothermal event at the JUAN01 site rather than a tectonic displacement.

---

## 10. Calibration Procedures

### 10.1 In-situ Intercomparison Protocol

The primary calibration verification procedure used by PSON is the in-situ pressure intercomparison, which compares each station's Paroscientific transducer against an independent high-accuracy CTD pressure sensor lowered to the station site from a ship. The procedure is conducted approximately every 18–24 months during scheduled servicing cruises.

The reference instrument used for all PSON intercomparisons is an SBE 37-SM or SBE 37-IM MicroCAT, selected based on the depth to be serviced (the IM variant is required for stations deeper than 4500 meters, presently applicable only to COAX01). The reference instrument is factory-calibrated annually by Sea-Bird Scientific and carries a stated accuracy of ±0.002% full-scale (approximately ±0.1 kPa). The PSON intercomparison achieves an effective precision of approximately ±0.005 kPa after accounting for thermal equilibration uncertainty, current-induced tilt of the CTD frame, and minor differences in the precise vertical position of the reference sensor relative to the station's pressure port.

The standard intercomparison protocol requires a minimum equilibration period of 60 minutes after the reference CTD is positioned at the station site, extended to 90 minutes at sites with elevated hydrothermal background such as JUAN01. A minimum of 10 hours of concurrent data collection is required to characterize any diurnal thermal drift that might affect the comparison. Data from the first 60–90 minutes are excluded from the calibration computation.

The gain and offset coefficients are derived by linear regression of the reference pressure against the raw sensor output over the intercomparison period. The gain is the slope of the regression and the offset is the intercept (converted to kPa units). The residuals of the regression are inspected for systematic structure that might indicate nonlinearity, and if residuals exceed the uncertainty budget by more than a factor of two, the intercomparison is flagged as inconclusive and rescheduled.

### 10.2 Laboratory Pre-Deployment Calibration

Before each deployment (or redeployment following a maintenance period), PSON instruments undergo a laboratory calibration check at the Oregon State University marine instrument facility using a dead-weight tester bench setup. The laboratory check verifies that the instrument's onboard firmware calibration is consistent with the factory calibration certificate and identifies any electronic component drift that occurred during storage. If the laboratory check reveals deviations exceeding 0.05% from the factory certificate, the instrument is sent to Paroscientific for recalibration before deployment.

The laboratory calibration procedure applies pressure steps at 10 values spanning 50% to 100% of the expected deployment pressure, with 15-minute dwell times at each step to allow thermal equilibration. The pressure stepping protocol follows PSON Calibration Procedure CG-12, Revision 3, which is maintained in the PSON technical documentation archive.

### 10.3 Post-Deployment Drift Tracking

For instruments operating continuously in the seafloor environment, slow crystal resonator drift is monitored by tracking the absolute calibrated pressure baseline at each station against the tidal prediction model. The tidal loading model, computed from the TPXO9 tidal solution, provides a reference prediction for the pressure at each station depth at each timestep. Deviations of the observed pressure from the tidal prediction, after subtracting the non-tidal oceanographic background estimated from satellite altimetry, provide a long-period drift signal that is tracked monthly.

If the derived drift exceeds 0.002 kPa per month, an alert is flagged in the PSON monitoring dashboard and the station's calibration record is reviewed for possible coefficient update. At NEMO01, where the 2023 calibration identified a substantial gain offset (1.12 vs. the 2020 value of approximately 1.05), the drift tracking data in retrospect showed a consistent upward trend in the baseline offset that began approximately 18 months before the formal recalibration, consistent with the known aging rate of the transducer crystal resonator under continuous operation.

---

## 11. Maintenance Logs: October 2023 Through December 2023

### 11.1 September 2023 Servicing Cruise: R/V Thomas G. Thompson, Cruise TN-391

The primary PSON servicing activity for 2023 was conducted during research cruise TN-391 aboard R/V Thomas G. Thompson, October 1–18, 2023. The cruise was co-funded by NSF-OOI infrastructure support and the Moore Foundation's Ocean Currents Initiative. Chief Scientist was Dr. James DeVries (OSU); co-chief scientist was Dr. Sofia Petrov (Scripps Institution of Oceanography). The ROV used for all servicing dives was Jason II, operated by WHOI ROV Group.

Servicing activities at AXID01 (Dive J2-1641, September 4): Battery pack replacement completed without incident. Pressure port screen cleaned of minor biofouling. Acoustic modem antenna repositioned to address 40-azimuth transmission dead zone. Post-replacement pressure intercomparison with SBE 37-SM reference (20-hour soak) completed; calibration coefficients for AXID01 confirmed as gain=1.0247, offset=−0.183 kPa, consistent with 2021 values.

Servicing activities at AXID02 (Dive J2-1642, September 5): Battery pack replacement completed. Minor corrosion on modem antenna bracket repaired with underwater epoxy. Pressure port screen cleaned. Post-replacement intercomparison (18-hour soak) completed; calibration coefficients confirmed as gain=0.9891, offset=+0.072 kPa.

Servicing activities at NEMO01 (Dive J2-1644, September 7): Battery pack replacement completed. Pressure port screen cleaned of extensive biofouling (thicker accumulation than at Axial sites, consistent with higher productivity in the slope environment). The intercomparison (14-hour soak, shortened by ROV scheduling conflict) revealed substantially different calibration from the pre-cruise expectation; gain coefficient updated to 1.12 and offset updated to +0.380 kPa. Post-dive review attributed the change to crystal resonator aging consistent with the instrument's 2017 factory calibration date.

Servicing at JUAN01 (Dive J2-1648, September 12): CTD intercomparison only; no battery or hardware servicing performed due to ROV arm malfunction earlier in the cruise. Intercomparison (11-hour soak, limited by weather) yielded calibration coefficients gain=1.0089, offset=+0.108 kPa. Full hardware servicing deferred to January 2024 scheduled window.

Servicing at COAX01 (not on this cruise; cable-connected station serviced via June 2023 dedicated cruise as described in Section 7.2).

NEMO02: Discovery of junction box flooding during AUV survey September 14. ROV recovery of onboard memory card during Dive J2-1650, September 15. Station placed in standby. Full servicing deferred to 2025.

### 11.2 JUAN01 January 2024 Maintenance Planning Notes

The scheduled January 2024 JUAN01 servicing window was confirmed by the PSON operations committee at the November 2023 quarterly meeting. The operation requires ROV access to the seafloor at the Juan de Fuca Ridge site and is planned for January 8 through January 12, 2024, aboard R/V Atlantis. The specific schedule is:

January 8: Ship arrival at JUAN01 site, ROV equipment checkout. Initial visual survey dive to confirm lander status and plan servicing sequence. Pressure sensor shutdown initiated for battery pack access.

January 9: ROV Dive J2-1667 planned for battery pack extraction and replacement. Main battery cage replacement is estimated to take 4–6 hours of bottom time. Data system reboot and initial function checks.

January 10: ROV Dive J2-1668 for tiltmeter reorientation and cable routing inspection. Post-reorientation functional verification. The tiltmeter reorientation will require physical contact with the lander frame and temporary changes to the orientation of the pressure port; pressure readings during this dive are unreliable.

January 11: Continued ROV activities: post-servicing pressure intercomparison CTD cast, verification of modem transmission. Results will be compiled onboard.

January 12: Ship departure from JUAN01 site. Data system restoration to normal autonomous operations mode.

Automated analysis pipelines should mark all JUAN01 pressure readings between January 8 and January 12, 2024 (inclusive) as operationally disturbed. Geophysical interpretations of JUAN01 data should exclude this window entirely.

### 11.3 Fourth Quarter 2023 Routine Operations Summary

October 2023: All active PSON stations operating nominally. COAX01 fiber connection experienced 2 hours of noise injection on October 17 associated with a reported splice-point issue on the cable, corrected remotely. NEMO02 placed in standby October 21 following AUV inspection findings described above. Data completeness across the active four stations: 99.1%.

November 2023: JUAN01 experienced a 14-hour acoustic communication gap beginning November 14 during the seismic swarm sequence referenced in Section 6.6. Data buffered onboard and transmitted in the following daily burst. AXID01 recorded two candidate slow-slip events in November, both subsequently confirmed by cross-station corroboration with AXID02. Data completeness across active stations: 97.8% (reduced by the JUAN01 communication gap).

December 2023: PSON operations committee meeting on December 4. Calibration error in COAX01 gain coefficient identified by Dr. Tanabe during her December data audit. Correction applied to calibration records effective January 2024 revision of dossier (this document). All four active stations operational at year end. Data completeness: 99.3%.

---

## 12. Incident Reports and Anomaly History

### 12.1 COAX01 Gain Coefficient Error — December 2023

During a systematic audit of the PSON calibration records conducted in December 2023, Dr. Yuki Tanabe of the PSON Calibration Working Group discovered a transposition error in the COAX01 gain coefficient. The original intercomparison data from the June 2023 servicing cruise clearly showed a gain of 0.9944, but when the value was entered into the dossier (Revision 7.2, released in July 2023) it was incorrectly typed as 0.9994. This error persisted through Revision 7.3 (October 2023) and is corrected in the present Revision 7.4.

The practical effect of the error was small: the gain difference of 0.005 corresponds to a scaling error of approximately 0.5% on calibrated pressure values. For a baseline pressure of 483 kPa, this produces an absolute error of approximately 2.4 kPa — too large to affect event detection (which operates on detrended anomalies much smaller than this) but large enough to affect absolute pressure comparisons with other data sources. The event catalog was not affected because the Z-score and Bayesian scoring stages operate on the detrended series, in which the absolute pressure bias cancels. However, any analysis comparing COAX01 calibrated pressures to tidal model predictions or to oceanographic reanalyses should apply the corrected gain of 0.9944 retroactively.

### 12.2 NEMO01 Calibration Drift Discovery — September 2023

The substantial recalibration of NEMO01 following the September 2023 intercomparison (gain updated from approximately 1.05 to 1.12, offset updated from approximately +0.16 kPa to +0.380 kPa) triggered a retrospective review of all NEMO01 catalog entries from the prior two years. The review was led by Dr. Morrison and took approximately three weeks of analysis time.

The conclusion of the review was that the drift in calibration had occurred gradually over the preceding 18–24 months and that the effect on the event catalog was primarily in event displacement magnitudes rather than event detection timing or frequency. Specifically, events in the 2022–2023 NEMO01 catalog with displacement estimates below 5 millimeters should be treated with caution, as the calibration uncertainty during the drift period was large enough to affect these estimates significantly. Events with displacement estimates above 1 centimeter are expected to be reliable to within 15% even accounting for the drift.

### 12.3 AXID01 Modem Ringing — Ongoing

The acoustic modem ringing artifact at AXID01 described in Section 2.4 has been investigated and is confirmed to be a persistent feature of this installation that cannot be eliminated without redesigning the acoustic modem placement relative to the pressure port. The PSON engineering team has implemented a software filter that flags modem transmission events in the database metadata, allowing automated analysis pipelines to exclude these samples. Users who process AXID01 data should query the metadata for modem transmission flags and set the corresponding pressure samples to null before applying the detrending and Z-score computation stages.

### 12.4 JUAN01 August 2023 Swarm Gap

The 14-hour data gap at JUAN01 during the August 2023 seismic swarm was caused by acoustic modem communication failure, likely due to elevated acoustic noise in the water column from the swarm's seismic emissions interfering with the modem's reception window. The gap extends from 2023-08-14T06:00Z to 2023-08-14T20:00Z. Data buffered onboard the instrument during this gap were transmitted in the subsequent daily burst and are fully recovered; they appear in the database with a gap-recovery quality flag.

The pressure record immediately preceding the gap shows a declining trend lasting approximately 6 hours with a total amplitude of approximately 0.15 kPa, which the PSON analysis team considers a possible slow-slip signal. However, because the event was followed by the communication gap and the record immediately after the gap is contaminated by the instrument's re-initialization sequence (which produces a brief pressure spike), the event cannot be rigorously characterized and is marked as a low-confidence candidate in the provisional catalog with a note that gap contamination prevents confident attribution.

---

## 13. Appendices

### Appendix A: Database Field Reference

The PSON relational database stores sensor readings in the `readings` table with the following columns: `id` (INTEGER, primary key, autoincrement), `station_id` (TEXT, foreign key to stations.code), `sensor_type` (TEXT, one of 'pressure', 'tilt_x', 'tilt_y', 'temperature'), `timestamp` (TEXT, ISO 8601 UTC format 'YYYY-MM-DDTHH:MM:SS.mmmZ'), `raw_value` (REAL, sensor output prior to secondary calibration), `unit` (TEXT, unit string for the raw value: 'kPa' for pressure, 'rad' for tilt, 'degC' for temperature).

The `stations` table has columns: `code` (TEXT, primary key, 5-character station identifier), `full_name` (TEXT), `latitude` (REAL, decimal degrees), `longitude` (REAL, decimal degrees, negative for west), `depth_m` (REAL), `deployment_date` (TEXT, 'YYYY-MM-DD'), `status` (TEXT, 'active' or 'standby').

Sensor type strings are lowercase and use underscores where needed. The tilt components are identified as `tilt_x` and `tilt_y` corresponding to approximately north-south and east-west horizontal components, respectively, in the instrument body frame. Tilt calibration and orientation correction for the body-frame tilt angles are not included in the standard pipeline and are described in a separate PSON tiltmeter calibration document.

### Appendix B: Sanctioned Base Images and Build Procedures

The PSON data processing toolkit is built and distributed as a containerized Node.js application using the TypeScript-compiled CLI tool `pson-changepoint` as the primary entry point. The tool accepts command-line arguments specifying the database path, the dossier path, and the output path, and produces a JSON event catalog conforming to the schema described in Section 9 and the output specification document.

Build procedure: from the repository root, run `npm ci` to install exact dependency versions from the lockfile, then `npm run build` to compile TypeScript to JavaScript. The compiled entry point is at `dist/src/index.js`. The tool is invoked as `node dist/src/index.js --db <db-path> --dossier <dossier-path> --output <output-path>`.

The SQLite database driver used is `better-sqlite3`, which requires a native compilation step during `npm ci`. The build system handles this automatically when `node-gyp` and appropriate system build tools are available; in the containerized environment, all required build prerequisites are pre-installed.

### Appendix C: Seismic and Volcanic Event Classification

The PSON event catalog classifies detected pressure anomalies into four primary types based on their spatial distribution across the array and their correlation with other geophysical observables:

Type I: Single-station events that appear at only one PSON station and show no correlation with seismicity in the OOI catalog. These are the most ambiguous class and include both genuine localized geophysical events (e.g., collapse of a hydrothermal vent chimney producing a localized pressure pulse) and instrument artifacts that survived the automated quality filters. Type I events are recorded in the catalog but flagged as low confidence unless independent corroborating evidence exists.

Type II: Multi-station events that appear coherently at two or more PSON stations within a propagation delay consistent with acoustic or seismic wave travel times. Type II events are the most common class in the catalog and include the episodic tremor and slip events associated with the Cascadia subduction zone and the volcanic inflation/deflation episodes at Axial Seamount. Cross-station coherence analysis for Type II events produces constraints on the source location through triangulation.

Type III: Single-station events that correlate with swarm seismicity in the OOI catalog or the NEPTUNE Canada network, suggesting that the pressure anomaly is produced by a seismic or volcanic source even if the event does not propagate coherently to adjacent stations. Type III events are typically short-duration (less than 3 hours) and may reflect events occurring close to the detecting station but too weak to trigger distant stations.

Type IV: Excluded events that appear in the raw catalog but are attributed to non-geophysical sources including maintenance windows, instrument artifacts, oceanographic phenomena, or other identified non-tectonic processes. The exclusion_reason field in the catalog output documents the specific attribution for each Type IV event.

### Appendix D: Bayesian Change-Point Algorithm Notes

The Bayesian change-point scoring procedure described in Section 9.5 is a simplified variant of the BOCP (Bayesian Online Change-Point Detection) algorithm introduced by Adams and MacKay (2007, arXiv:0710.3742) and the Bayesian Evidence for Change-Point Estimation (BECPE) method developed by Dr. Petrov and colleagues. The specific implementation used in the PSON pipeline prioritizes computational efficiency for long continuous time series over the full generality of the original algorithms.

Key implementation considerations: The log Bayes factor computation assumes Gaussian noise with variance estimated from the MAD-based sigma. This approximation is valid for the bulk of the PSON data and produces accurate confidence scores in the 0.6–0.99 range for events with peak Z-scores above 4.0. For events with Z-scores between the threshold and 4.0, the Gaussian approximation begins to break down and confidence scores should be interpreted with somewhat higher uncertainty.

The scale_factor parameter of 2.0 in the sigmoid transformation was tuned empirically by the PSON analysis team using a set of 30 manually labeled events from the 2022–2023 period at AXID01 and NEMO01. The labeled set included 18 confirmed tectonic events and 12 confirmed false positives. Using scale_factor = 2.0, the sigmoid confidence score correctly ranked all 18 true events above 0.65 and 10 of 12 false positives below 0.50, with the two false positives that scored above 0.50 attributable to an unusual cluster of oceanographic pressure pulses during a 2023 deep-water current event.

### Appendix E: Data Access and Contact Information

The PSON data archive is maintained by the PSON Data Management Group at Oregon State University. All PSON data are eventually released through the IRIS/EarthScope data management system under the network code ZN. Real-time and near-real-time data for COAX01 (the cable-connected station) are available through the Ocean Networks Canada data archive portal. Data from acoustic-modem-connected stations (AXID01, AXID02, NEMO01, JUAN01) are uploaded daily and available with a nominal latency of 28 hours. 

Contact for data issues, calibration questions, and collaboration inquiries: pson-data@ceoas.oregonstate.edu. For instrument servicing and deployment logistics: pson-ops@mbari.org. For Bayesian analysis pipeline questions: sofia.petrov@scripps.edu.

Publications using PSON data should cite the network data release DOI (10.17591/PSON-DATA-2024) and reference this dossier as the calibration authority document.

---

## 14. Extended Operational Notes: 2022–2023 Geophysical Highlights

### 14.1 The October 2022 Axial Deflation Sequence

The most scientifically significant event captured by the PSON array in 2022 was a multi-week sequence of pressure anomalies at AXID01 and AXID02 beginning in late October and extending through mid-November 2022. The sequence started with a 4-hour pressure drop at both Axial stations on October 29 with amplitudes of approximately 0.3 kPa, suggesting a rapid deflation of the magma reservoir beneath Axial Seamount consistent with either a shallow dike intrusion or rapid lava effusion on the caldera floor.

This initial deflation was followed by a series of smaller pressure oscillations lasting through the following three weeks, interpreted as a combination of re-pressurization episodes and fault accommodation responses to the deflation-induced stress changes. The PSON pressure analysis was complemented by OOI seismograph data showing swarm activity concentrated in a region southeast of the caldera axis, and by OOI broadband ocean bottom seismometer records showing low-frequency tremor consistent with fluid migration in the upper crust.

The event sequence provided an important test of the detection pipeline's ability to handle complex multi-event scenarios. The initial large-amplitude event was correctly detected at both Axial stations simultaneously and classified as a Type II multi-station event by the automated catalog. The subsequent smaller oscillations were more challenging; several fell below the detection threshold at one station while exceeding it at the other, and careful manual review was required to assemble the complete picture.

### 14.2 November 2022 Cascadia Slow-Slip Sequence

A series of episodic slow-slip events on the upper Cascadia megathrust was detected at NEMO01 during November 2022. Three distinct episodes were identified, each lasting 10–24 hours with pressure amplitudes of 0.08–0.15 kPa, which at the network conversion factor correspond to vertical displacements of 8–15 millimeters. The events were observed to correlate with periods of elevated non-volcanic tremor detected by the Pacific Northwest Seismic Network, providing strong evidence for their tectonic origin.

At the time of the November 2022 events, the NEMO01 calibration was based on the 2020–2021 coefficients, which subsequent analysis showed were drifting from the true values due to crystal aging. The displacement estimates for the November 2022 events are therefore subject to calibration uncertainty; the PSON team's retrospective analysis suggests the true displacements were approximately 10–20% larger than the catalog values, consistent with the calibration correction ultimately applied in September 2023.

### 14.3 JUAN01 February 2023 Ridge-Crest Events

In February 2023, JUAN01 recorded three distinct pressure anomalies on February 11, 14, and 19, each lasting 3–5 hours with amplitudes of 0.10–0.18 kPa. The three events were analyzed jointly and attributed to a sequence of shallow fault creep episodes on the Juan de Fuca Ridge segment south of the VENTS-1 hydrothermal vent field. The spatial correlation with the vent field and the shallow depth of the inferred events are consistent with the hypothesis that tectonic loading of ridge-crest normal faults periodically releases through episodic creep, producing both the observed pressure anomalies and elevated diffuse hydrothermal flow that has been documented at the vent field during similar episodes in the past.

All three February 2023 events were flagged by the automated detection pipeline and survived the manual review process. They are included in the PSON event catalog as Type III events (single-station, correlated with seismicity) due to the absence of coherent signals at other array stations, which are located more than 100 kilometers from JUAN01.

### 14.4 Discussion: Inter-Station Consistency Checks

The PSON analysis team performs regular inter-station consistency checks to validate the calibration of the array. These checks compare the long-period pressure baseline at each station against the global tidal prediction and against each other using differential pressure analysis. The differential pressure between AXID01 and AXID02, after calibration, should be nearly constant (varying only with local oceanographic differences) and show no long-term drift. In practice, the differential has varied by less than 0.05 kPa over the network's lifetime, which is within the uncertainty budget of the calibration procedure.

The consistency checks also serve to detect anomalies in the calibration coefficients: if the differential pressure between two stations that share a common oceanographic environment begins to trend, it suggests that one station's calibration is drifting relative to the other. This type of relative monitoring was what motivated the discovery of NEMO01's calibration drift in 2023 — the differential between NEMO01 and the tidal model showed a trend inconsistent with any known oceanographic mechanism, which ultimately led to the realization that the gain coefficient had drifted from its earlier value.

---

## 15. Instrument Quality Standards and Procurement Notes

### 15.1 Paroscientific Digiquartz Transducer Procurement

The PSON network specifies Paroscientific Digiquartz 8B-series pressure transducers as its standard instrument for all primary pressure monitoring deployments. The full-scale pressure rating used across the network is 7000 psia (equivalent to approximately 48,000 kPa), providing a comfortable safety margin above the maximum deployment pressure at COAX01 (approximately 48,300 kPa), although PSON will evaluate whether the next COAX01 instrument should be upgraded to the 10,000 psia variant to provide greater margin.

Procurement of new instruments requires a minimum six-month lead time due to factory calibration scheduling at Paroscientific's Redmond, Washington facility. Each unit receives a full calibration certificate documenting temperature coefficients, linearity characteristics, and long-term stability test results. PSON maintains a calibration reference log tracking the serial number, factory calibration date, and in-situ calibration history of every instrument in the fleet.

### 15.2 Battery Technology

The primary battery packs used at PSON stations are lithium primary cells in a custom aluminum pressure housing designed by the PSON engineering team and fabricated by Seabird Electronics (not to be confused with Sea-Bird Scientific, the CTD manufacturer). Each pack contains 96 individual D-cell lithium cells in a 24S4P configuration providing approximately 400 watt-hours at standard temperatures. The expected service life at nominal 10-minute sampling with daily acoustic modem transmission is 36 months, with a 20% derating applied for cold deployment temperatures (below 2°C). All active PSON stations except NEMO02 (in standby) are currently operating within their expected battery life.

Battery replacement during ROV servicing dives requires the mated connector to the electronics housing to be physically separated and reconnected, which produces a brief data gap (typically 2–5 minutes) visible in the database records as a gap in the timestamp sequence. These battery-change gaps are flagged in the database quality metadata and should be excluded from detrending window computations.

### 15.3 Data Telemetry Standards

All PSON acoustic modem links use LinkQuest UWM2000H modems operating in the 20–30 kHz frequency band with a nominal data rate of 600 baud under favorable propagation conditions. Daily burst transmissions are scheduled during periods of minimal acoustic interference from ship traffic, typically between 02:00 and 04:00 UTC. Each daily burst transmits the previous 24 hours of buffered data plus instrument health telemetry including battery voltage, electronics temperature, and modem received signal strength.

The station clocks are GPS-disciplined via the acoustic modem's GPS receiver during each transmission window, which synchronizes the onboard clock to UTC to within approximately 10 milliseconds. Clock drift between transmission windows is monitored and has never exceeded 500 milliseconds in the network's operational history.

---

## 16. Seismological Context and Geophysical Background

### 16.1 The Juan de Fuca Tectonic System

The PSON network's scientific mandate is anchored in the complex geophysics of the Juan de Fuca tectonic system, which encompasses a relatively small (500 km × 300 km) oceanic plate being subducted beneath North America along the Cascadia Subduction Zone. Unlike the much larger Pacific Plate subducting further west, the Juan de Fuca Plate is young (0–10 million years old) and therefore hotter and more buoyant, making its subduction dynamics distinctly different from those of the old, cold Pacific Plate.

The Cascadia subduction zone extends from northern California to southern British Columbia and represents one of the most seismically hazardous regions in North America. The geological record, preserved in coastal marsh sediments and turbidite sequences, documents a history of great earthquakes (Mw 8.0–9.2) with recurrence intervals of 200–500 years, the most recent of which occurred in January 1700 CE. Between these great earthquakes, the plate interface accommodates plate motion partly through slow creep events detectable by PSON pressure monitoring and partly through locking that accumulates elastic strain destined to be released in future earthquakes.

### 16.2 Axial Seamount Volcano Dynamics

Axial Seamount, the host site for the AXID01 and AXID02 stations, is the most magmatically active submarine volcano on the Juan de Fuca Ridge and one of the most comprehensively monitored seafloor volcanoes in the world. Its caldera, a roughly elliptical depression approximately 8 km long and 3 km wide, has been the site of lava eruptions in 1998, 2011, 2015, and 2022 — a recurrence rate that makes it an extraordinary natural laboratory for studying magmatic processes.

The inflation-deflation cycles of Axial's magma reservoir produce large, unambiguous pressure signals detectable by the PSON array and by the OOI seafloor pressure and tilt networks. During the inflationary phases between eruptions, the caldera floor rises at rates of 10–60 centimeters per year as melt accumulates in the shallow reservoir (approximately 2–3 km depth), producing sustained pressure increases at AXID01 and AXID02 that can reach 5–10 kPa over six-month periods. The eruptions produce rapid deflation events (0.5–30 kPa over hours to days) as magma drains from the reservoir and erupts along fissure vents.

The 2022 eruption, which occurred in February of that year during a period of intense OOI monitoring activity, provided PSON's most detailed eruption record to date. AXID01 recorded a 6.2 kPa pressure drop over approximately 20 hours, and AXID02 recorded 5.9 kPa drop over the same period. The small difference between the two stations reflects the slightly different distances and orientations of the two landers relative to the inferred deflation source beneath the caldera floor. Analysis of the 2022 eruption data is ongoing.

### 16.3 Hydrothermal Vent Dynamics and the JUAN01 Observation Window

The unique scientific opportunity at JUAN01 — monitoring pressure dynamics in an active hydrothermal vent field — comes with the observational complexity described in Section 6.3 but also with the potential for novel discoveries at the interface of tectonic, volcanic, and hydrothermal processes. Hydrothermal vent fields at mid-ocean ridges are powered by a combination of magmatic heat and exothermic chemical reactions between seawater and hot crustal rocks; the stability of these fields is perturbed by seismic and volcanic events that alter the permeability structure of the crust through which hydrothermal fluids circulate.

Previous work at the ASHES vent field on Axial Seamount has shown that slow-slip events on ridge-axis faults produce measurable perturbations in hydrothermal vent fluid chemistry and flux rates, consistent with a tectonic stress-mediated permeability change mechanism. The JUAN01 pressure record provides an independent constraint on this coupling because fault creep events that change crustal permeability should simultaneously produce detectable seafloor pressure anomalies (from the vertical deformation component) and changes in the local hydrothermal pressure structure (from the fluid pressure perturbation component).

Disentangling these two contributions to the JUAN01 pressure record is an active area of research for the PSON science team, and contributions from graduate students Elena Rodriguez (OSU) and James Chen (UW) on this topic are forthcoming in the literature.

### 16.4 Deep Cascadia Basin Observations (COAX01)

The Cascadia Basin abyssal plain, where COAX01 is deployed, is not directly above the subduction interface but is positioned on the incoming oceanic plate as it approaches the trench. Observations from this location contribute to understanding of the state of stress in the incoming plate and the oceanographic pressure environment at the seaward reference end of the subduction zone.

Previous work using autonomous pressure floats in the Cascadia Basin documented pressure anomalies of 0.01–0.05 kPa associated with the passage of slow-slip events that had been identified on land using GPS geodesy. These anomalies were very small and at the margin of detection capability for float-based instruments; COAX01's permanently installed instrument with its lower noise floor is expected to provide more reliable detections. However, the elevated oceanographic background discussed in Section 7.3 has so far dominated the detection statistics at COAX01, and only the first hints of tectonic signal have been observed in the 22-month record available at the time of this writing.

---

## 17. Quality Assurance and Peer Review Protocols

### 17.1 Automated Quality Control

The PSON data pipeline performs automated quality control (QC) checks at each stage of processing, from the initial telemetry receipt to the final calibrated time series in the database. The automated QC checks are divided into three tiers:

Tier 1 (immediate rejection): Samples that fall outside the physically plausible range for each sensor type at each station depth. Pressure samples below 0 kPa or above 150% of the nominal depth pressure are immediately flagged as invalid. Temperature samples below −2°C (below freezing for seawater) or above 10°C (implausibly warm for PSON depths) are flagged. Tilt samples exceeding ±10,000 micro-radians are flagged.

Tier 2 (conditional flagging): Samples that fail spike detection (values exceeding 5 sigma from the rolling 6-hour median are flagged as potential spikes unless the spike persists for more than 30 minutes, in which case it is demoted to a transient anomaly flag rather than a spike flag). Step-change detection identifies instances where consecutive samples differ by more than 0.1 kPa without a preceding continuous trend, flagging potential electronic resets.

Tier 3 (contextual flags): Samples during documented maintenance windows, samples following modem transmission events (for AXID01 and the modem ringing issue), and samples near the beginning of data segments following power cycles. These Tier 3 flags do not necessarily indicate bad data but alert downstream analysts to conditions requiring contextual interpretation.

### 17.2 Semi-Annual Scientific Review

Twice per year, the PSON science team convenes a data quality review meeting at which the six-month record for each active station is examined by at least two scientists independently. The review examines the calibrated pressure baseline against the tidal model, the event catalog for coherence with other observational networks, and the noise statistics for signs of calibration drift. Findings from each review are documented in the operational log and may trigger requests for unscheduled servicing.

The June 2023 review identified the potential calibration drift at NEMO01 that was subsequently confirmed during the September 2023 cruise; this demonstrates the value of the regular review cycle for catching slow-onset issues that do not trigger the automated QC checks. The December 2023 review identified the COAX01 gain transcription error, again demonstrating the value of the human oversight layer.

### 17.3 External Calibration Audits

The PSON Calibration Working Group conducts an external calibration audit every two years using an independent instrument not part of the PSON fleet. The audit uses a high-accuracy pressure standard maintained at the National Institute of Standards and Technology (NIST) via a pressure transfer standard calibrated in Gaithersburg, Maryland. The PSON group's primary reference MicroCAT instruments are calibrated against this NIST chain at each audit cycle, and the calibration traceability is documented for inclusion in publications using PSON data.

The most recent external audit was conducted in March 2023. All PSON primary reference instruments were found to be within their stated accuracy specifications relative to the NIST-traceable standard. The next audit is scheduled for spring 2025.

---

## 18. PSON Data Use Agreement and Acknowledgment Requirements

### 18.1 Data Use Agreement

All users of PSON data obtained through the network data archive or any authorized distribution channel agree to the following terms:

1. PSON data are made available for scientific research and educational purposes. Commercial use of PSON data requires a separate data use license from Oregon State University.

2. Published analyses using PSON data must cite the network data DOI and this calibration dossier as the primary reference for calibration parameters. Specific publications generating the data (e.g., the network description paper by DeVries et al., in preparation for JGR: Solid Earth) should be cited when available.

3. Known data quality issues and limitations described in this dossier should be acknowledged in publications. In particular, the NEMO01 calibration drift issue (Section 12.2) and the COAX01 gain coefficient transcription error (Section 12.1) should be noted in any analysis using those stations' data from the relevant periods.

4. Users who identify previously undocumented data quality issues are encouraged to report them to the PSON data management group at pson-data@ceoas.oregonstate.edu so that corrections can be incorporated into future dossier revisions.

### 18.2 Acknowledgment Text

Publications using PSON data should include the following acknowledgment text: "Seafloor pressure, tilt, and temperature data from the Pacific Seafloor Observatory Network (PSON) were obtained through the PSON data archive. PSON operations are supported by the National Science Foundation Ocean Sciences Division (grant OCE-1654474), the Gordon and Betty Moore Foundation, and Ocean Networks Canada. Calibration services are provided by the PSON Calibration Working Group at Oregon State University and Scripps Institution of Oceanography."

---

## Revision History

Revision 7.4 — January 2024: Corrected COAX01 gain coefficient (0.9994 → 0.9944). Updated NEMO01 calibration coefficients following September 2023 servicing (gain 1.05 → 1.12, offset +0.16 → +0.380 kPa). Updated AXID01 and AXID02 calibration confirmations from September 2023 servicing. Added JUAN01 January 2024 maintenance planning notes. Updated Q4 2023 operations log. Formalized Bayesian change-point scoring algorithm description. Added Section 14 geophysical highlights.

Revision 7.3 — October 2023: Added Q3 2023 maintenance log including NEMO02 standby placement. Preliminary NEMO01 calibration update. Added COAX01 extended noise characterization notes.

Revision 7.2 — July 2023: Added COAX01 June 2023 calibration results (with gain later found to have transcription error). Updated JUAN01 calibration from September 2023 intercomparison. Added Section 12 incident reports for 2022 events.

Revision 7.1 — January 2023: Added AXID02 tiltmeter orientation note. Updated NEMO01 detection parameters following 2022 calibration review. Added Section 14 deep Cascadia basin context.

Revision 7.0 — July 2022: Initial release incorporating COAX01 following March 2022 deployment. Reorganized station sections into current format.

---

*End of Document — Pacific Seafloor Observatory Network Operations and Calibration Reference Dossier, Revision 7.4*

*Prepared by the PSON Data Management Group, Oregon State University / UW MBARI Joint Program*
*Contact: pson-data@ceoas.oregonstate.edu*

---

## 19. 2021 Deployment Expedition: Detailed Field Log

### 19.1 Pre-Cruise Preparation and Instrument Testing

The July 2021 deployment expedition, designated cruise TN-359 aboard R/V Thomas G. Thompson, represented the first major PSON network expansion since the original Axial array installations in 2016 and 2018. Pre-cruise preparation began in April 2021 with a comprehensive laboratory testing campaign at the OSU College of Earth, Ocean, and Atmospheric Sciences instrument facility in Corvallis, Oregon. Each instrument destined for deployment — including the Paroscientific transducers, Applied Geomechanics tiltmeters, Aanderaa thermistors, battery packs, and acoustic modems — was subjected to a full functional checkout before being transferred to the ship at the Port of Seattle on July 7.

The AXID01 pressure transducer (serial number 140297) completed its factory calibration at Paroscientific's Redmond facility on May 3, 2021. The factory calibration certificate documented full-scale linearity within 0.008% and temperature sensitivity coefficient of 3.2 parts per million per degree Celsius, parameters consistent with Paroscientific's standard specification for the 8B7000-I series. Post-receipt testing at OSU in late May confirmed that the instrument's digital output matched the factory calibration to within 0.01 kPa at simulated depths from 0 to 4500 meters using the OSU dead-weight tester. The Paroscientific unit destined for AXID02 (serial number 140298) was tested on May 28 and showed equivalent performance, with slightly different temperature sensitivity (2.9 ppm/°C) and excellent pressure linearity (0.006% full scale).

Battery pack testing included capacity verification under cold conditions. Each pack was fully charged, refrigerated to 2°C for 48 hours to simulate seafloor temperature, and discharged at the nominal 10-minute sampling load to verify rated capacity. Three of the five packs intended for deployment reached 98–100% of rated capacity; two packs showed marginally lower capacity (92–94%), consistent with the allowable range in the PSON procurement specification, and were approved for deployment after review by instrument technician Matthew Chen.

### 19.2 Deployment Operations: July 8–20, 2021

The Thompson departed Seattle on July 7, 2021 at 18:00 PDT and arrived at the Axial Seamount operational area on July 10 at 06:15 UTC after a 36-hour transit across the Washington-Oregon continental shelf and abyssal plain. Conditions upon arrival were favorable, with 2.3-meter significant wave height and 10-knot northwest winds. Chief Scientist Dr. DeVries convened the full science-ROV team for a safety and operations briefing on the evening of July 9 during transit.

**July 10: AXID01 Deployment (Jason Dive J2-1547)**

The AXID01 lander was assembled on deck beginning at 04:00 on July 10 and completed by 07:30. Pre-dive inspection included a final pressure sensor functional check, acoustic modem link test (confirmed two-way communication with the ship's topside modem), and battery connection verification. The lander was lowered over the starboard crane at 08:15 and the Jason ROV was deployed at 09:45. Bottom time at 4145 meters was achieved at 11:22 UTC.

ROV pilot Jerry Adamson conducted an initial survey of the designated landing site on the south caldera rim, approximately 400 meters from the nearest active hydrothermal field. The survey revealed that the originally designated coordinates placed the site on a slightly elevated basalt pillow feature that would have compromised the tripod frame's stability. Pilot Adamson relocated the target approximately 15 meters to the southwest, where a flat basalt bench provided an ideal foundation. The relocation was approved by Dr. DeVries in consultation with the science party.

The lander was lowered from the crane line and guided into position by the ROV at 12:47 UTC. Three epoxy anchor bolts were injected into cracks in the basalt using the ROV's anchor injection tool, and the lander frame legs were seated into the injection holes at 13:15. Post-seating stability testing — involving the ROV applying a lateral force of approximately 50 Newtons to the frame — confirmed that the installation was secure. The acoustic modem communication test conducted from the ROV at 13:45 confirmed that the lander was transmitting correctly and that the GPS-synchronized clock had set successfully.

The ROV recovered to the ship by 16:20, and the ship received the first autonomous data transmission from AXID01 at 02:18 UTC on July 11 — the first of what would become a continuous daily telemetry record.

**July 12: AXID02 Deployment (Jason Dive J2-1549)**

AXID02 was deployed on July 12 during a slightly more challenging sea state (3.2-meter significant wave height, 15-knot winds). The deployment proceeded without major incident, with the lander placed on a sediment-covered area 185 meters south-southwest of AXID01 as planned. Bottom time was achieved at 11:08 UTC. The landing site required helical screw anchor installation rather than epoxy bolts due to the soft sediment substrate; the ROV's screw anchor tool performed the installation in approximately 35 minutes. Data transmission from AXID02 was confirmed at 02:14 UTC on July 13.

**July 14–16: Northern Slope and Ridge Crest Installations**

NEMO01 was deployed on July 14 in comparatively favorable conditions on the continental slope. The NEMO01 site on the upper slope presented a complication not encountered at the Axial sites: a moderate near-bottom current of approximately 8 centimeters per second from the north was pushing the ROV off the site during precise positioning operations. Pilot Adamson compensated by using the ROV's dynamic positioning thrusters to maintain station, consuming additional battery capacity that required an unscheduled mid-dive battery swap at 14:30 UTC. The NEMO01 lander was seated by 15:45 and confirmed stable.

JUAN01 was deployed on July 16, beginning with an extended site survey dive on the Juan de Fuca Ridge crest. This was the most complex deployment of the expedition because the ridge-crest environment required careful routing of the lander frame through regions of active hydrothermal chimneys, collapsed basalt formations, and seafloor bacterial mat communities. A preliminary survey dive on July 15 (J2-1554) identified three candidate sites; the science party selected the site that offered the best combination of flat substrate, proximity to the target monitoring area, and distance from the nearest active black smoker cluster (to minimize thermal noise and risk of sediment resuspension from the hydrothermal plume). The installation at the selected site was completed on July 16, J2-1556, with the lander seated by 14:22 UTC.

**July 17–19: AXID01 and AXID02 Follow-Up Checks**

An unscheduled check dive (J2-1557) was conducted on July 17 to visually confirm the AXID01 installation following a brief communication anomaly detected in the overnight telemetry at 03:40 UTC. The dive revealed that the modem antenna had shifted slightly in the current and was directing its transmission beam at a suboptimal azimuth relative to the ship track. ROV manipulator adjustments corrected the antenna orientation, and subsequent telemetry confirmed full communication quality. The communication anomaly was attributed to the original antenna orientation rather than any hardware fault.

Inspection of AXID02 during the same dive found the installation in good condition with no anomalies noted.

**July 20: Expedition Conclusion and Transit**

All PSON deployments in the July 2021 expedition were completed by July 19, with initial telemetry confirmed from all four new stations. A final ocean observation cast at the Axial caldera site at 08:00 UTC on July 20 collected water column data for calibration context, and the Thompson departed for Seattle at 12:00. The vessel arrived at Pier 36, Seattle, on July 22.

### 19.3 Initial Data Quality Assessment: July–August 2021

The first month of data from the four new stations was analyzed by research scientist Dr. Anika Rodriguez in August 2021 to establish baseline noise characteristics and confirm calibration. The assessment compared calibrated pressure values against the TPXO9 tidal model and against the pre-existing AXID01 and NEMO01 records from the earlier 2016 and 2018 deployments (which have since been decommissioned).

Pressure baselines at all four stations were consistent with the expected depth-pressure relationship within the calibration uncertainty budget. Tidal signal amplitudes at the Axial sites matched model predictions to within 2%, a strong confirmation that the calibration coefficients derived in the initial laboratory testing were appropriate for the deployment conditions.

One notable anomaly in the initial assessment was a sustained positive offset of approximately +0.28 kPa in the JUAN01 calibrated pressure during the first 72 hours of operation. Dr. Rodriguez's analysis attributed this offset to thermal disequilibrium between the instrument housing and the surrounding seawater: the lander had been stored in a climate-controlled environment before deployment and was slightly warmer than the ambient seafloor temperature at 2318 meters. The offset decayed exponentially with a time constant of approximately 18 hours, consistent with the thermal mass of the titanium housing and battery pack assembly. After 72 hours, the JUAN01 pressure baseline stabilized within 0.03 kPa of the expected value, and no further anomalous offset was observed.

The tilt records at AXID01 and AXID02 both showed the expected very low signal levels during the first month, with no detectable inflation signal and noise levels consistent with the Applied Geomechanics 702 tiltmeter specifications. A minor oscillation at the tidal period was detectable in the AXID01 tilt record and was attributed to the elastic deformation of the caldera floor under tidal loading, consistent with theoretical predictions for the elastic moduli of fresh basalt at that depth.

---

## 20. Oceanographic Background Signals and Their Management

### 20.1 Tidal Pressure Loading at PSON Depths

Among the many oceanographic signals that impose pressure variability on the seafloor at PSON depths, tidal loading is by far the largest in amplitude. The semi-diurnal and diurnal tidal harmonics produce pressure variations of 0.5–2.5 kPa peak-to-peak at the PSON station depths, with the exact amplitude depending on the station's position relative to the amphidromic points of the Northeast Pacific tidal system. These tidal pressure variations are far larger than the slow-slip event signals that PSON is designed to detect, but they also have a precisely predictable character: given the station coordinates and depth, the tidal loading contribution can be computed to within a few percent using global tidal solutions such as TPXO9.

However, PSON's analysis pipeline does not subtract the tidal model prediction explicitly. Instead, the 10-day quadratic detrending approach described in Section 9.3 effectively removes the tidal signal because the detrending window is long enough to observe multiple complete tidal cycles and fit the combined secular trend plus tidal variation. The polynomial detrend of degree 2 over a 10-day window removes not only the tidal signal but also the slow secular drift and the lowest-frequency oceanographic variability, which are the dominant competing signals for slow-slip detection.

The reason for using the data-adaptive detrending rather than model-based tidal subtraction is robustness: the data-adaptive approach does not require access to a tidal model or accurate station coordinates during processing, and it is immune to uncertainties in the tidal model that can reach several percent in regions of complex bathymetry like the Juan de Fuca Ridge. For most PSON applications, the data-adaptive approach achieves equivalent or better tidal removal than model-based methods.

There is one limitation of the data-adaptive approach worth noting: if a slow-slip event occurs during the detrending window, the event signal itself will partly contaminates the estimated detrend polynomial, leading to a slightly underestimated detrended anomaly. For events lasting less than 10% of the detrending window (less than 1 day in a 10-day window), this contamination is negligible. For longer events, the detrending procedure should be modified to exclude the event window from the trend estimation, which can be done iteratively: perform an initial detection, identify event windows, recompute the detrend excluding those windows, and re-run detection on the improved detrended series.

### 20.2 Mesoscale Eddy Pressure Variability

Mesoscale oceanic eddies — rotating features with horizontal scales of 50–300 kilometers and vertical scales extending from the surface to depths of 500–2000 meters — impart pressure perturbations at the seafloor through two mechanisms. The direct mechanism is the isostatic response of the deep ocean to the mass redistribution associated with the eddy's density structure: the cyclonic (cold, dense) eddies slightly depress the seafloor pressure, while anticyclonic (warm, light) eddies raise it. The indirect mechanism, which is often larger, is the barotropic pressure signal associated with the eddy's sea surface height anomaly, which propagates to the seafloor on sub-inertial timescales.

The combined eddy pressure perturbation at PSON depths ranges from approximately 0.02 to 0.20 kPa, depending on the eddy's strength and proximity. These perturbations evolve on timescales of days to weeks, which means they are partially removed by the 10-day detrending window but can leave significant residuals when eddy evolution is rapid (e.g., during eddy-eddy interactions or eddy shedding from the continental slope).

COAX01 is most strongly affected by mesoscale eddy variability because of its open abyssal plain setting far from the topographic barriers that partially shield the other PSON stations. NEMO01 is similarly exposed, while the Axial stations benefit from the topographic shielding of the ridge-caldera complex. JUAN01 sits in a ridge-controlled current environment that attenuates eddy signals through wave scattering.

The 10-day detrend window was chosen partly to balance tidal removal (requiring at least 3 full tidal cycles, or about 3.5 days) against mesoscale eddy residual minimization (requiring the window to be short enough to track eddy evolution). Analysis by Dr. Petrov using synthetic event injection tests showed that a 10-day window produces false alarm rates below 5% per year due to residual eddy signals at NEMO01 and COAX01, whereas a 7-day window produces false alarm rates of 8–12% per year at those stations and a 14-day window has slower response to fast-evolving events.

### 20.3 Internal Wave Pressure Variability

Internal waves, generated at the thermocline and propagating in the deep ocean on timescales of minutes to hours, create pressure perturbations at the seafloor that are much smaller than tidal or mesoscale eddy signals. At PSON depths (2000–5000 meters), internal wave pressure variance at the 10-minute sampling interval is typically 0.001–0.005 kPa root-mean-square, comparable to or smaller than the instrument noise floor. These signals do not present a significant interference challenge for the PSON slow-slip detection pipeline.

An exception occurs at JUAN01, where the complex topography of the Juan de Fuca Ridge generates anomalously energetic internal wave activity. Observations from an ADCP mooring near the JUAN01 site have documented current velocities associated with internal waves of up to 5 centimeters per second at depths near 2000 meters, considerably stronger than the typical abyssal values. The associated pressure variability contributes to JUAN01's elevated background noise level and is one of several factors motivating the station-specific noise characterization documented in Section 6.

### 20.4 Barometric Pressure Loading (Inverted Barometer Effect)

Variations in atmospheric pressure at the sea surface produce corresponding pressure variations at the seafloor through the inverse barometer (IB) effect: a 1 hPa increase in atmospheric pressure produces an approximately 1 hPa (0.1 kPa) increase in seafloor pressure, and vice versa. For the Northeast Pacific, mid-latitude storm systems typically produce sea-level pressure variations of 5–30 hPa over periods of 1–5 days, corresponding to seafloor pressure changes of 0.5–3 kPa — a significant signal in the context of slow-slip event detection.

PSON has historically relied on the detrending algorithm to remove the IB contribution without explicit atmospheric correction, and this approach is effective for slowly evolving atmospheric systems whose pressure signature is captured by the detrending window. However, for rapidly deepening cyclones or fast-moving frontal systems, the IB contribution can evolve faster than the detrending window can track. This has occasionally caused pressure anomalies attributable to atmospheric forcing to appear in the early-stage detection pipeline. The solution implemented in the post-2022 version of the automated catalog is to cross-reference detected candidate events against ERA5 atmospheric reanalysis data: if a candidate event coincides with a significant IB signal at the station's surface position, it is flagged as a potential atmospheric contaminant and subjected to enhanced manual review before catalog acceptance.

---

## 21. Extended Case Studies of Detected Events

### 21.1 AXID01 Event: October 29–November 2, 2022 Deflation Sequence

The October 2022 Axial Seamount deflation sequence is the highest-amplitude event in the PSON catalog to date and provides an instructive example of how the standard detection pipeline handles a large, complex event. The sequence began with a rapid pressure drop at both AXID01 and AXID02 starting at approximately 2022-10-29T08:30 UTC.

At AXID01, the raw database readings showed a sustained decrease in calibrated pressure of 0.3 kPa over 4 hours, followed by a partial recovery of approximately 0.08 kPa over the next 18 hours, followed by a second smaller pressure drop of 0.12 kPa on October 30. The detrended time series at AXID01, computed with the 10-day rolling quadratic window, showed a prominent negative excursion beginning at the onset time and persisting for approximately 72 hours before returning to the pre-event baseline. The peak Z-score for the main event window was 47.3 standard deviations, well above any realistic detection threshold, making this event trivially detectable by any reasonable automated method.

More instructive for understanding the detection pipeline's behavior was the treatment of the secondary pressure features following the main deflation. The partial re-pressurization on October 29–30 and the second drop on October 30 produced Z-score excursions of 8.2 and 12.5 standard deviations, respectively, when analyzed as separate candidate windows. The Bayesian scoring step assigned confidence scores of 0.94 and 0.97 to these secondary features, confirming them as genuine events. The catalog therefore contains three related entries for the October 2022 sequence rather than a single merged event, which is the intended behavior: the pipeline identifies individual statistically coherent anomaly windows rather than attempting to merge complex multi-phase sequences into composite events.

The displacement estimates for the three October 2022 entries were −0.030 m, +0.008 m (re-pressurization), and −0.012 m (second drop), for a net cumulative deflation of approximately −0.034 m over the 72-hour sequence. This is consistent with seismic moment estimates for the intrusion derived by the OOI seismograph network. Cross-station corroboration with AXID02 was confirmed, with AXID02 showing a coherent pressure sequence with peak Z-score of 42.1 and displacement estimates within 5% of those at AXID01.

### 21.2 NEMO01 Events: November 2022 Cascadia Slow-Slip Sequence

The three distinct slow-slip episodes detected at NEMO01 in November 2022 — on November 7, 14, and 21 — provide an example of how the PSON pipeline handles episodic events with similar characteristics that occur in a relatively short time window.

The November 7 event had a peak Z-score of 6.8 standard deviations (above the 4.0 threshold for NEMO01), a duration of 11.5 hours, and a mean detrended calibrated pressure anomaly of −0.093 kPa, corresponding to a displacement estimate of −0.0093 m (−9.3 mm). The Bayesian confidence score for this event was 0.88. Both the duration and amplitude characteristics are consistent with episodic tremor and slip (ETS) events documented by the land-based GNSS network in the region, which typically produce vertical GPS displacements of 5–15 mm at coastal stations 100–200 km to the northeast of NEMO01.

Notably, using the old (pre-September 2023) NEMO01 calibration coefficients (gain approximately 1.05, offset approximately +0.16 kPa), the displacement estimate for this event would have been computed as −0.087 kPa × 0.1 m/kPa = −0.0087 m — approximately 6.5% smaller than the corrected value. For a displacement of 9.3 mm, a 6.5% error represents approximately 0.6 mm of systematic underestimation. While this is below the practical detection threshold for the land-based network (GNSS accuracy for vertical position is typically ±3–5 mm), it illustrates how calibration errors compound over time and can affect quantitative geophysical interpretations.

The November 14 and 21 events were structurally similar to the November 7 event, with peak Z-scores of 5.9 and 7.3 standard deviations, durations of 9.2 and 14.1 hours, and displacement estimates of −0.0078 m and −0.011 m respectively. The three events are spaced at intervals of exactly 7 days — a periodicity that, if genuine, could suggest a resonant behavior of the slow-slip source region. However, the PSON team and collaborators caution that with only three events in the sequence, the apparent periodicity is statistically marginal, and the spacing may be coincidental.

### 21.3 JUAN01 Events: February 2023 Ridge-Axis Creep Episodes

The three ridge-crest creep events detected at JUAN01 in February 2023 illustrate the challenges and opportunities of operating a pressure monitor in a hydrothermal vent field environment. The events were detected on February 11, 14, and 19 by the automated pipeline.

For the February 11 event, which occurred at 2023-02-11T16:00 UTC and lasted approximately 4.5 hours, the automated catalog initially misattributed the event to a "thermal backflow" episode (Type IV, excluded) because the temperature channel showed an anomaly of +0.04°C coinciding with the pressure change. However, manual review by Dr. Rodriguez found that the temperature anomaly was secondary to the pressure change — the temperature rose after the pressure change, not simultaneously — and the temperature signature was consistent with the adiabatic warming of rising hydrothermal fluids forced upward by the tectonic displacement rather than indicating horizontal advection of a hydrothermal plume over the lander. The event was reclassified as a Type III (single-station, seismically correlated) tectonic event.

This case illustrates the importance of the temperature-pressure timing relationship in distinguishing tectonic from hydrothermal events at JUAN01. The detection pipeline now includes an option to compute the cross-correlation lag between temperature and pressure anomalies for events at JUAN01; a lag of less than 15 minutes (temperature leading pressure) suggests horizontal plume advection, while a lag of 15 minutes or more (pressure leading temperature) suggests a tectonic source producing adiabatic temperature effects in the fluid column above the lander.

### 21.4 COAX01: Deep Abyssal False Positive Investigation, September 2022

The first catalog entry from COAX01, recorded in September 2022, was subsequently determined to be a false positive attributable to Antarctic Bottom Water variability. The event appeared in the preliminary automated catalog on September 18–19, 2022, with a peak Z-score of 5.3 standard deviations (just above the 5.0 threshold) and a duration of 5.2 hours — long enough to exceed the 4.0-hour minimum duration criterion. The displacement estimate was +0.012 m.

Post-event analysis by Dr. Tanabe used deep current meter data from the OOI Regional Cabled Array's profiler mooring approximately 85 km from COAX01, which showed a distinct pulse of cold, dense Antarctic Bottom Water arriving at the Cascadia Basin floor during the same period as the COAX01 pressure anomaly. The density contrast between the incoming Antarctic Bottom Water and the ambient abyssal Pacific water produces a pressure increase at the seafloor that closely mimics a tectonic compression signal. The density-pressure relationship, combined with the magnitude of the current velocity pulse observed at the OOI mooring, is fully consistent with the 0.012 kPa anomaly observed at COAX01, confirming the oceanographic attribution.

Following this investigation, the PSON analysis team added the Antarctic Bottom Water flag to the exclusion criteria for COAX01 events, requiring cross-reference with deep current meter data before a COAX01 detection is accepted into the confirmed catalog. The November 2022 candidate event at COAX01 was similarly rejected after the same cross-reference procedure showed a coincident Bottom Water pulse.

---

## 22. Instrument Engineering: Pressure Sensor Mechanics

### 22.1 Paroscientific Digiquartz Operating Principle

Understanding the engineering basis of the Paroscientific Digiquartz pressure transducer is helpful for interpreting the calibration corrections that are central to this dossier. The instrument operates on the principle of quartz crystal resonance: a thin quartz beam is held in mechanical tension or compression by the pressure applied to the instrument's sensing diaphragm, and the beam's resonant frequency changes in proportion to the applied stress. By accurately measuring the resonant frequency of the quartz beam, the instrument computes pressure using a model derived from the crystal's mechanical properties.

The key advantage of this approach over resistive or capacitive pressure transducers is the extraordinary frequency stability of quartz crystal resonators: the resonant frequency of a well-characterized crystal can be measured to better than 0.001 Hz out of a nominal resonant frequency of approximately 40 kHz, a relative precision of 2.5 × 10⁻⁸. This corresponds to a pressure precision at the 4000-meter deployment depth of approximately 0.001 kPa — the noise floor specification of the Paroscientific 8B7000-I.

The principal limitation of the quartz resonator principle is its temperature sensitivity. The resonant frequency of a quartz beam changes with temperature, not only because of the direct thermal expansion of the beam but also because the elastic moduli of quartz are temperature-dependent. Factory calibration characterizes these temperature effects to high accuracy using a polynomial temperature compensation model, but imperfect characterization introduces a residual temperature-dependent error that is partially absorbed into the gain and offset corrections determined during the in-situ intercomparisons. Monitoring the instrument's onboard temperature channel alongside the pressure channel provides valuable diagnostic information for assessing whether an apparent pressure change is instrument-related or environmental.

### 22.2 Crystal Resonator Aging and Frequency Drift

All quartz crystal resonators exhibit a phenomenon known as secular frequency drift, in which the resonant frequency changes slowly over time even under constant temperature and pressure conditions. The physical origin of this drift is not fully understood but is attributed to slow relaxation processes in the crystal lattice, including stress relaxation at crystal-holder interfaces, and possibly to atomic diffusion within the crystal structure itself.

For the Paroscientific 8B7000-I instrument, the manufacturer specifies a long-term drift rate of less than 0.02 kPa per year. In practice, the PSON experience has been that drift rates increase with instrument age: instruments in their first three years of service show drift rates of 0.005–0.010 kPa per year, while instruments five or more years old (such as NEMO01's instrument) may show drift rates of 0.02–0.05 kPa per year. This is consistent with literature reports from other long-term seafloor pressure monitoring programs, including the DART network and the ODP/IODP borehole observatories.

The aging effect was prominently illustrated in the NEMO01 calibration update following the September 2023 servicing cruise. The NEMO01 instrument, in continuous service since 2017 (a period of six years at the time of the intercomparison), showed a gain of 1.12 — a 12% departure from unity that represents the cumulative effect of crystal drift over this extended deployment period. This large departure is at the high end of the expected range for a six-year-old instrument and may indicate that NEMO01's crystal resonator has experienced above-average aging due to the particular temperature and pressure conditions at the 3822-meter deployment site.

### 22.3 Pressure Port Maintenance

The pressure port — the physical interface between the open seawater environment and the sensing diaphragm of the Paroscientific transducer — requires periodic maintenance to prevent fouling from marine organisms and particulate matter that could create a restricted flow path and introduce biases in the pressure measurement. The titanium mesh screen protecting the pressure port has a nominal pore size of 50 micrometers, which is fine enough to exclude most benthic organisms but allows free flow of seawater under normal conditions.

In practice, the screens at NEMO01 and the Axial stations accumulate measurable fouling in the late summer and autumn months, consistent with the annual cycle of biological production in the overlying water column. At NEMO01, the September 2023 servicing dive found the most extensive fouling in the network: the screen was approximately 40% occluded by a combination of bacterial mats, foraminiferal tests, and fine sediment particles that had accumulated over the three years since the previous cleaning. The PSON team estimates that this level of fouling could introduce a systematic pressure bias of up to 0.05 kPa through flow restriction, though the detrending algorithm would remove most of this bias as a slowly evolving offset.

The September 2023 cleaning procedure used a soft brush tool mounted on the ROV manipulator to mechanically disturb the fouling material, followed by a water jet from the ROV's thruster to flush the loosened material away from the port. Post-cleaning pressure readings confirmed that the baseline shifted by approximately 0.03 kPa immediately following the cleaning, consistent with the estimated fouling bias, before stabilizing at the new lower baseline within 2 hours.

---

## 23. Data Management and Archive Standards

### 23.1 Database Schema Evolution

The PSON relational database schema has evolved through four major versions since the network's inception in 2016. The current schema (version 4.0, deployed in 2021 alongside the AXID01/AXID02 deployment) standardized the timestamp format to ISO 8601 UTC with millisecond precision (format string: YYYY-MM-DDTHH:MM:SS.mmmZ), added the stations table to store geographic metadata alongside the readings, and introduced the index on (station_id, sensor_type, timestamp) that substantially improves query performance for station-specific time series extraction.

The evolution from schema version 3.0 to 4.0 was motivated by growing data volume (the addition of AXID01 and AXID02 tilt channels significantly increased the row count) and by community feedback that the earlier timestamp format (UNIX epoch seconds as a floating-point field) was inconvenient for direct visual inspection and for queries involving date-range filtering. The ISO 8601 format is now consistent with IODP database standards and facilitates straightforward import into common data analysis platforms.

A known consideration for SQL queries against the readings table is that timestamp ordering works correctly with lexicographic (string) comparison because the ISO 8601 format is designed to be lexicographically ordered: a string comparison `timestamp > '2024-01-15T04:00:00.000Z'` correctly selects all readings after January 15, 2024 at 04:00 UTC. Users implementing time-range queries should use string comparison directly rather than attempting to convert timestamps to numeric types, which would require parsing overhead.

### 23.2 Data Archive Backup and Redundancy

PSON follows a three-tier data backup strategy. The primary data store is the PostgreSQL database at OSU's College of Earth, Ocean, and Atmospheric Sciences server farm, which is backed up nightly to a secondary server at the University of Washington School of Oceanography. A tertiary backup is maintained on the MBARI data archive system in Moss Landing, California. The three backup locations are geographically separated to protect against regional disasters, and quarterly restoration tests verify that all three copies can be successfully restored to a functional database.

In addition to these server-based backups, the raw acoustic modem telemetry packets are archived permanently in their compressed binary format on tape storage at OSU and at WHYCOS. These packet archives provide a raw data foundation that could be reprocessed from scratch if the database were ever corrupted or if future calibration advances warrant a complete reanalysis of the archive.

The SQLite-format database distributed to analysis users (including the snapshot used for the January 2024 detection catalog described in this dossier) is a lightweight export of the PostgreSQL archive that prioritizes portability and offline analysis capability over the scalability features of the production system. The SQLite format is appropriate for analyses spanning one to several months of data from the five active stations, which involves fewer than 100,000 rows at the nominal 10-minute sampling interval.

### 23.3 Data Release Timelines

PSON follows a one-year proprietary period for new data from the AXID01, AXID02, and NEMO01 stations, after which data are released openly through the IRIS/EarthScope data management system. JUAN01 data are released on a six-month proprietary cycle due to the station's co-management with the OOI network. COAX01 data are released in near-real-time (latency below 48 hours) given the station's fiber cable connection and the co-investigators' commitment to rapid public data access as a condition of the Moore Foundation funding.

The current January 2024 PSON dataset provided to analysis collaborators represents data that is either within the current proprietary period (AXID01, AXID02, NEMO01) or in the standard OOI semi-annual release cycle (JUAN01), and has been shared under the PSON data use agreement described in Section 18. COAX01 data in the dataset are already publicly available through Ocean Networks Canada.

---

## 24. Advanced Notes on Detection Algorithm Tuning

### 24.1 Sensitivity-Specificity Tradeoffs at Each Station

The detection parameters described in the station-specific sections (Sections 2–7) represent operating points on the receiver operating characteristic (ROC) curve for each station's detection pipeline. The ROC curve describes the tradeoff between true positive rate (sensitivity — the fraction of genuine slow-slip events that are detected) and false positive rate (1-specificity — the fraction of non-events that are incorrectly classified as detections).

For the Axial stations (AXID01, AXID02), operating at a threshold of 3.5 sigma and minimum duration 2.0 hours places the operating point at an estimated sensitivity of approximately 95% (for events with displacement > 5 mm) and a false positive rate of approximately 1 per year. These estimates were derived from a Monte Carlo simulation study conducted by Dr. Petrov in which synthetic events of varying amplitudes and durations were injected into 12 months of background AXID01 pressure data, and the detection pipeline was run on the augmented dataset.

For NEMO01, the operating point at 4.0 sigma and 3.0 hours duration yields an estimated sensitivity of 88% for displacement events greater than 8 mm and a false positive rate of approximately 2 per year — higher than the Axial stations but acceptable given the station's higher noise environment. The sensitivity drops below 80% for events smaller than 5 mm displacement at NEMO01 because such events produce Z-scores that frequently fall below the 4.0-sigma threshold.

For COAX01, the extreme threshold of 5.0 sigma and 4.0 hours minimum duration is estimated to provide 75% sensitivity for displacement events larger than 15 mm, with a false positive rate of approximately 0.5 per year. The sensitivity penalty at COAX01 is the deliberate cost of maintaining a manageable false positive rate in the high-noise abyssal environment. Improving COAX01 sensitivity would require either significantly reducing the threshold (unacceptable false positive rate) or improving the physical noise environment (not currently feasible).

### 24.2 Rolling versus Fixed-Window MAD Computation

The recommended practice of computing the MAD over the full analysis month (as described in Section 9.4) reflects a design choice between two alternative approaches. The first alternative — rolling MAD over a short window (e.g., 24 hours) — would provide a locally adaptive noise estimate that could track changes in the background noise level over time. The second alternative — the recommended full-month MAD — provides a stable, globally representative noise estimate that is unaffected by local noise fluctuations.

The rolling-window approach was evaluated by the PSON analysis team in 2021 and rejected for three reasons. First, if the rolling window is too short, the MAD estimate can be inflated by the presence of a slow-slip event itself within the window, causing the Z-score to be suppressed at the center of the event and potentially causing missed detections. Second, the rolling MAD introduces edge effects near the boundaries of data gaps that can produce spurious elevated Z-scores immediately after a gap closes. Third, the full-month MAD provides a useful characterization of the overall noise level that is valuable for inter-station and inter-period comparisons independent of event detection.

The minimum analysis window required for a stable MAD estimate is approximately 10 days at the 10-minute sampling interval, providing approximately 1440 samples per station-sensor combination. Using less than 10 days of data for the background MAD computation is not recommended because shorter windows may underestimate the dispersion if the window falls within a geophysically quiet or noisy period, biasing the Z-score level in either direction.

### 24.3 Multi-Station Joint Analysis

For events that produce coherent pressure anomalies at multiple PSON stations, the confidence in the slow-slip attribution can be substantially improved by a joint multi-station analysis. The basic version of this approach computes a weighted average of the Z-scores at each station, where the weights are inversely proportional to the station's background MAD (i.e., quieter stations receive higher weight). The joint Z-score is then compared against a combined threshold appropriate for the joint statistic.

A more sophisticated approach computes the expected delay and amplitude ratio between pairs of stations for a hypothetical event at a candidate source location, then searches over source locations to find the position that maximizes the coherence of the observed multi-station signatures. This location-solving approach requires a physical model of how slow-slip events propagate pressure signals through the water column and the crust, which adds complexity but provides the additional benefit of a crude event-location estimate.

The PSON analysis team has implemented both the weighted-average and the location-solving approaches for use with the two-station Axial array (AXID01 and AXID02), where the known station separation and geometry simplifies the location problem. Extension to the full five-station network is an active research and development effort, with a preliminary joint analysis paper in preparation by Elena Rodriguez as part of her dissertation research at OSU.

---

## 25. PSON Network Expansion Plans: 2024–2027

### 25.1 NEMO02 Redeployment

As noted in Section 5, NEMO02 was placed in standby following a junction box flooding incident in October 2023 and is a priority for redeployment during the 2025 servicing cruise. The redeployment plan involves a complete replacement of the junction box assembly with an updated design featuring improved O-ring sealing geometry that addresses the failure mode observed in the October 2023 incident. The pressure transducer and battery pack will also be replaced; the old transducer (serial 135891) will be returned to Paroscientific for factory recalibration and may be redeployed as a spare unit in a future network expansion.

The NEMO02 site coordinates (47.2891° N, 128.7204° W, 3694 m depth) will be reused unless the AUV survey preceding the redeployment reveals new concerns about site stability or sediment dynamics. The science team anticipates that redeployment at the original site will restore the full NEMO two-station capability for upper Cascadia slow-slip triangulation that was lost in October 2023.

### 25.2 Proposed TRENCH01 Installation

The PSON expansion plan approved by the network's science steering committee in September 2023 includes a new station designated TRENCH01, to be positioned on the décollement immediately landward of the trench axis at approximately 46.5° N, 127.0° W at a depth of approximately 2800 meters on the accretionary prism. This location is scientifically valuable because it would provide the first direct pressure measurement from the wedge toe region, where the deep slow-slip events that COAX01 is attempting to detect from the subducting plate would be much closer to the measurement point.

Deployment of TRENCH01 faces several technical challenges. The accretionary prism is characterized by active faulting, gas venting, and sediment instability, all of which could threaten instrument stability over the multi-year deployment timescale targeted. Geotechnical assessment of the proposed site using sub-bottom profiler data from OOI Leg 389 in 2022 suggests that the top 5–10 meters of sediment at the target location are susceptible to slow creep of approximately 2 cm per year on the dominant fault planes, which would likely cause gradual tilting of a tripod-mounted lander at an unacceptable rate.

The PSON engineering team is investigating borehole installation as an alternative to surface lander deployment at TRENCH01. A borehole installation, in which the pressure sensor is cemented into a 50-meter borehole drilled by an IODP-style coring system, would provide excellent coupling to the solid earth and immunity to surface sediment instability. However, borehole installation requires specialized IODP ship time and a significantly larger budget than standard lander deployments; the operations committee has requested a feasibility study and cost estimate before committing to this approach.

### 25.3 AXID01 Replacement and Upgrade

Planning is underway for a scheduled replacement of the AXID01 Paroscientific transducer during the next major servicing cruise, tentatively planned for summer 2026. The AXID01 instrument (serial 140297, factory-calibrated May 2021) will be approximately five years old at that point and approaching the service window where increased crystal drift rates are expected. Proactive replacement before measurable drift occurs is more cost-effective than waiting for performance degradation.

The replacement transducer has been identified in the PSON instrument inventory (serial 143087, factory-calibrated November 2023) and is currently in storage. The new unit incorporates the latest version of Paroscientific's temperature compensation firmware, which the manufacturer claims reduces the aging drift rate by approximately 30% compared to older firmware versions. This claim has not been independently verified by PSON but is consistent with the physical improvements to crystal mounting geometry described in the 2023 Paroscientific product update bulletin.

### 25.4 Enhanced Telemetry Infrastructure

The PSON steering committee has authorized an upgrade of the acoustic modem telemetry infrastructure at AXID01 and AXID02 to enable higher data rate transmissions, reducing the latency from the current 24-hour daily burst cycle to 6-hour bursts. This upgrade would provide significantly more timely detection of rapid geophysical events (such as the October 2022 deflation sequence) by the automated pipeline. The upgrade requires replacement of the current LinkQuest UWM2000H modems with the newer UWM4000HDP units, which operate at higher power but support data rates up to 4800 baud versus the current 600 baud, enabling 6 times more data per unit time.

Power budget calculations show that the UWM4000HDP units, operating at 6-hour burst intervals, would consume approximately 40% more battery power per day than the current configuration. This reduces the expected battery life from 36 months to approximately 26 months, which the operations committee accepted as a reasonable tradeoff for the improved data timeliness. The upgrade is planned for the 2026 servicing cruise in conjunction with the AXID01 transducer replacement.

---

## 26. Supplementary Calibration Reference Data

### 26.1 Reference CTD Instrument Specifications

For completeness, the specifications of the SBE 37-SM MicroCAT CTD used as the reference instrument for all PSON in-situ intercomparisons (AXID01, AXID02, NEMO01, JUAN01) are as follows. The instrument carries a Druck PDCR 4000 resonant pressure sensor with a factory-calibrated accuracy of ±0.002% full-scale (±0.1 kPa for the 6000 dbar rated version). Temperature accuracy is ±0.001°C, and conductivity (for salinity) is ±0.003 mS/cm. The SBE 37-SM is rated to 7000 meters depth and was last factory-calibrated at Sea-Bird Scientific in January 2023.

The SBE 37-IM MicroCAT used at COAX01 (depth 4831 m, requiring the deep-rated variant) was factory-calibrated in April 2023. Its pressure sensor is a Digiquartz resonant pressure sensor (manufactured by Paroscientific for Sea-Bird Scientific) rated to 10,000 meters, with factory-calibrated accuracy of ±0.001% full-scale (±0.1 kPa for the 10,000 dbar rated version).

Both reference CTDs are maintained under a Sea-Bird Scientific annual calibration service agreement, which provides annual factory recalibration with full documentation. The PSON calibration chain is therefore traceable to the NIST-calibrated standards used by Sea-Bird Scientific's calibration laboratory in Bellevue, Washington.

### 26.2 Intercomparison Data Quality Checks

During each in-situ intercomparison, the PSON calibration team applies a standard set of quality checks to the raw intercomparison data before deriving calibration coefficients. These checks include:

Thermal equilibration check: A plot of the reference CTD pressure versus time during the first 90 minutes is inspected for monotonic convergence to a stable value. If the convergence is not monotonic or if the rate of change at the end of the equilibration period exceeds 0.001 kPa per 10 minutes, the equilibration period is extended.

Regression residual check: The residuals of the linear regression between the PSON station output and the reference CTD are plotted against time to check for systematic structure. Systematic residual trends (e.g., a linear drift in the residuals over the comparison period) indicate that one of the instruments is experiencing a temperature-related transient rather than being fully equilibrated. If residuals show trends larger than 0.003 kPa per hour, the comparison period is split and separate regressions are computed for the early and late portions; if the derived coefficients differ by more than 0.01 in gain or 0.01 kPa in offset, the comparison is flagged for re-analysis.

Outlier check: Individual data points more than 3 sigma from the regression line are inspected. Physical disturbances (e.g., the CTD frame swinging in a current pulse) can create brief pressure transients; these are identified and removed from the regression if they are isolated single-sample events.

### 26.3 Historical Calibration Record

The following table summarizes the gain and offset values from all completed PSON calibrations since network inception. These historical values provide context for assessing calibration stability over time.

AXID01 Calibration History: July 2021 factory pre-deployment check (gain 1.024, offset −0.176 kPa); September 2023 in-situ intercomparison (gain 1.0247, offset −0.183 kPa). The small changes between these two measurements — 0.0007 in gain (0.07%) and 0.007 kPa in offset — are within the combined uncertainty budget of the factory check and the in-situ intercomparison and confirm that AXID01's crystal resonator has been highly stable during its first two years of operation.

AXID02 Calibration History: July 2021 factory pre-deployment check (gain 0.989, offset +0.070 kPa); September 2023 in-situ intercomparison (gain 0.9891, offset +0.072 kPa). Again, changes are minimal (0.0001 in gain, 0.002 kPa in offset), confirming stability.

NEMO01 Calibration History: September 2020 factory pre-deployment check (gain 1.049, offset +0.162 kPa); August 2021 in-situ intercomparison (gain 1.052, offset +0.168 kPa); September 2023 in-situ intercomparison (gain 1.12, offset +0.380 kPa). The step change between the August 2021 and September 2023 values — 0.068 in gain (approximately 6.5%) and 0.212 kPa in offset — is much larger than the changes seen at the Axial stations and is consistent with accelerated crystal resonator aging in this instrument.

JUAN01 Calibration History: 2019 original deployment factory check (instrument since replaced); July 2021 post-upgrade factory pre-deployment check (gain 1.008, offset +0.104 kPa); September 2023 in-situ intercomparison (gain 1.0089, offset +0.108 kPa). The small changes confirm that JUAN01's replacement instrument (installed in 2021) is behaving in a stable manner consistent with a relatively young crystal resonator.

COAX01 Calibration History: March 2022 factory pre-deployment check (gain 0.994, offset −0.153 kPa); June 2023 in-situ intercomparison (gain 0.9944, offset −0.156 kPa). The modest changes are consistent with the instrument's recent factory calibration and short deployment history.

---

## 27. Interdisciplinary Connections and Collaborative Programs

### 27.1 OOI Regional Cabled Array Integration

The Pacific Seafloor Observatory Network operates in close scientific coordination with the Ocean Observatories Initiative (OOI) Regional Cabled Array (RCA), which provides independent pressure, seismograph, and oceanographic measurements across much of the Juan de Fuca Plate and the Cascadia margin. The two networks are complementary: OOI provides denser station coverage with real-time Internet-connected data access, while PSON provides independent calibrated pressure time series that serve as a cross-check on OOI's earthquake and geodesy catalog.

The primary formal collaboration between PSON and OOI is a data exchange agreement, renewed annually, under which PSON provides daily calibrated pressure time series to the OOI data archive within 48 hours of receipt, and OOI provides PSON with access to the RCA seismograph catalog and hydrophone data in near-real-time. This exchange has been scientifically productive on multiple occasions, including during the October 2022 Axial deflation sequence when the combined PSON-OOI dataset enabled a significantly more detailed characterization of the event than either network could provide independently.

### 27.2 GNSS Geodesy Integration

Land-based GNSS (GPS) geodesy provides the primary long-period constraint on Cascadia subduction zone strain accumulation and episodic slow-slip events. The PSON seafloor network provides a complementary offshore record that extends the geodetic aperture to the plate interface region that is not sampled by any land-based geodetic network.

The PSON-GNSS collaboration is coordinated through the Pacific Northwest Geodetic Array (PANGA) at Central Washington University, which operates approximately 160 continuous GNSS sites in Washington, Oregon, and British Columbia. When PSON detects a slow-slip candidate event at NEMO01 or JUAN01, the PSON data management group alerts the PANGA team within 24 hours, and the PANGA team checks their archive for corresponding GNSS displacements at coastal stations. If GNSS evidence supports the seafloor detection, the combined evidence is submitted to the PSON-PANGA event catalog maintained jointly by the two programs.

The most detailed PSON-GNSS joint analysis to date examined the November 2022 Cascadia slow-slip sequence. This analysis found that the three pressure episodes at NEMO01 on November 7, 14, and 21 each coincided with GPS displacement bursts at coastal GNSS stations in northwest Washington and southern British Columbia, with displacements of 2–6 mm in the direction of plate convergence reversal (southwestward) consistent with episodic creep on the interface at 15–20 km depth. The joint paper by Rodriguez, DeVries, and Chen is in review.

### 27.3 NEPTUNE Canada Hydrophone Network Integration

The NEPTUNE Canada network, operated by Ocean Networks Canada from the University of Victoria, includes seafloor hydrophone arrays along portions of the Juan de Fuca and Explorer plates and at several sites on the continental margin. These hydrophones detect both seismic and volcanic acoustic signals and provide event timing and approximate location estimates that complement PSON's pressure-based approach.

The principal use of NEPTUNE Canada data in PSON analyses is cross-validation of tectonic origin for single-station PSON events, particularly those at JUAN01. A slow-slip event at JUAN01 that coincides with elevated acoustic emission rates on the NEPTUNE Canada hydrophone array is much more likely to be of tectonic origin than an event with no hydroacoustic counterpart. The February 2023 ridge-crest creep events discussed in Section 21.3 all had hydroacoustic counterparts in the NEPTUNE Canada record, providing strong corroboration for their tectonic attribution.

---

*This document contains all calibration parameters, operational procedures, and detection standards necessary for the analysis of PSON pressure time series data. For questions about specific data values, contact pson-data@ceoas.oregonstate.edu. For questions about the detection methodology, contact sofia.petrov@scripps.edu.*

*PSON Operations and Calibration Reference Dossier, Revision 7.4 — January 2024*
*Confidential — Distribution limited to authorized PSON collaborators and data users*

---

## 28. Scientific Background: Slow-Slip Event Physics

### 28.1 Mechanics of Episodic Tremor and Slip

Episodic tremor and slip (ETS) events were first recognized in the Cascadia subduction zone in the early 2000s through the combination of GPS geodesy and seismic tremor observations. These events are now understood to be a widespread phenomenon along subduction zones globally, occurring in a depth range of approximately 25–45 km on the plate interface, in a rheological transition zone between the fully locked shallow interface (where great earthquakes nucleate) and the freely slipping deep interface. The ETS zone corresponds roughly to the depth at which elevated pore fluid pressures and elevated temperatures bring the interface close to, but not at, the failure stress threshold, enabling episodic aseismic sliding.

In Cascadia, ETS events occur with a roughly 14-month recurrence interval and involve slip of 1–3 centimeters on fault patches extending hundreds of kilometers along strike. Individual ETS events are composed of numerous sub-events (the episodic tremor component) that together produce a cumulative geodetic signal detectable by GNSS at the surface. The relationship between these deep ETS events and the shallower, shorter-duration slow-slip signals detectable by the PSON seafloor array is an active research topic. The shallow slow-slip events at PSON detection depths (2000–5000 meters, corresponding to interface depths of roughly 5–20 km) likely represent a distinct population of events occurring at shallower, drier, and cooler conditions on the plate interface — potentially related to the transition from sediment-dominated décollement near the trench to more competent plate interface at depth.

The Cascadia ETS events do produce detectable signals in the PSON record, but their signatures are different from the shallow slow-slip events. Because ETS slip occurs at depths of 25–45 km, roughly 100–150 km from the trench, the vertical displacement of the seafloor produced by these deep events is spread over a broad region (hundreds of kilometers in extent) and is correspondingly small in amplitude at the seafloor surface. NEMO01, the PSON station best positioned to detect ETS signals, typically sees pressure anomalies of 0.005–0.020 kPa during ETS episodes — at or near the detection threshold for that station — compared to the 0.08–0.15 kPa anomalies that NEMO01 detects during shallow slow-slip events.

### 28.2 Volcanic Deformation Detection

The PSON array stations on Axial Seamount (AXID01, AXID02) are ideally positioned to detect the inflation and deflation cycles of the Axial magma system, which operates on a 3–7 year eruption recurrence cycle. The pressure changes associated with volcanic inflation (caused by accumulation of melt in the sub-caldera magma body) are much larger in amplitude than slow-slip signals, reaching several kilopascals per year during the inter-eruption inflationary phase, but evolve slowly enough that they appear in the low-frequency detrended record as a steady background trend rather than as discrete anomalous events.

Discrete volcanic events detected by the PSON pipeline are typically associated with rapid changes in inflation rate — accelerations that occur during intrusive episodes when melt migrates from the deep reservoir into shallower dikes — or with the eruption events themselves, which produce rapid deflation of tens of kilopascals over hours to days. The October 2022 deflation event described in Section 21.1, at 0.3 kPa in 4 hours, represents a modest but unambiguous example; the February 2022 eruption, producing 6.2 kPa deflation, was substantially larger and dominated the AXID01 and AXID02 records for the entire month.

The PSON detection pipeline is not specifically designed to classify volcanic versus tectonic events — it identifies anomalous pressure departures from the background and reports them with a confidence score. Geophysical classification is performed in the downstream event review stage, informed by the OOI seismograph catalog, the NEPTUNE hydrophone array, and (for eruption events) the AUV visual survey data that typically documents fresh lava flows. The event catalog's exclusion_reason field may be used to note oceanographic or maintenance-related exclusions but is not used to encode geophysical classification.

### 28.3 Hydrothermal Pressure Dynamics Near JUAN01

The Juan de Fuca Ridge vent field in the vicinity of JUAN01 is part of a network of high-temperature (300–400°C) and diffuse low-temperature (5–50°C) hydrothermal systems that extends along approximately 60 kilometers of the ridge crest. These systems are driven by the heat flux from a shallow magma body (estimated depth 1–3 km below the ridge seafloor) and are modulated by tectonic stress changes, earthquakes, and eruptions that alter the permeability of the fractured basalt through which hydrothermal fluids circulate.

The coupling between tectonic stress and hydrothermal permeability is relevant to the interpretation of JUAN01 pressure data because fault creep events that produce the pressure anomalies detected by the PSON pipeline also transiently alter the permeability of the surrounding rock, changing the fluid pressure distribution in the sub-seafloor hydrothermal system. This secondary hydrothermal response is superimposed on the primary tectonic signal and can either amplify or dampen the observed pressure anomaly depending on the geometry of the fault and the fluid flow network.

Separating the primary tectonic component from the secondary hydrothermal response at JUAN01 is theoretically possible using a coupled tectonic-hydrothermal model, but this requires detailed knowledge of the subsurface permeability structure that is not currently available at the JUAN01 site. The practical approach adopted by the PSON team is to accept the combined signal as the observable and focus on the temporal characteristics (duration, rise time, symmetry) as diagnostic indicators: pure tectonic signals tend to have a rapid onset and a slower asymmetric recovery, while hydrothermal-dominated responses tend to be more symmetric and temperature-correlated. This distinction is imperfect but provides useful guidance for manual event review.

---

## 29. Quality Control Event Log: January 2024

### 29.1 AXID01 January 2024 Overview

The AXID01 station entered January 2024 with a clean data record from the December 2023 period. Calibration confirmation from the September 2023 servicing cruise confirms gain of 1.0247 and offset of −0.183 kPa remain applicable for all January 2024 data. No maintenance activities are planned at AXID01 during January 2024. Background noise levels measured during the first week of January were consistent with the long-term average of 0.005 kPa RMS in the detrended record.

The AXID01 Z-score threshold of 3.5 sigma and minimum duration criterion of 2.0 hours apply to all January 2024 pressure data analysis. No quality flags have been issued for AXID01 in January 2024 through the preparation date of this revision. The station is operating normally and its daily telemetry bursts have been received without interruption. Battery voltage telemetry indicates a charge state of approximately 87%, consistent with the expected depletion rate for this unit (installed September 2023, approximately 4 months into a 36-month service life).

### 29.2 AXID02 January 2024 Overview

AXID02 entered January 2024 operating normally, with calibration parameters of gain 0.9891 and offset +0.072 kPa. The station shares the same detection parameters as AXID01 (Z-score threshold 3.5 sigma, minimum duration 2.0 hours). Background noise in early January 2024 was measured at 0.0049 kPa RMS in the detrended record, marginally quieter than the December 2023 average and consistent with reduced mesoscale eddy activity in the region, as documented by satellite altimetry.

AXID02 battery voltage is at approximately 91%, slightly higher than AXID01 due to the marginally lower modem power consumption at AXID02's slightly more favorable transmission geometry. Both Axial stations are expected to operate without battery replacement well into 2026.

### 29.3 NEMO01 January 2024 Overview

NEMO01 entered January 2024 with the revised calibration parameters documented in Section 4.2: gain 1.12 and offset +0.380 kPa. These revised parameters should be applied to all NEMO01 data processed in January 2024 and all subsequent periods. The Z-score threshold for NEMO01 is 4.0 sigma with a minimum duration of 3.0 hours.

Background noise at NEMO01 in early January 2024 was elevated relative to the December 2023 average (0.0081 kPa RMS vs. 0.0068 kPa RMS), attributable to increased mesoscale eddy activity documented in the region by the Copernicus Marine Service satellite altimetry product during the first week of January. This elevated noise condition does not trigger automatic quality flags (the noise is still well within the range described in Section 4.3) but users should be aware that the detection threshold effectively corresponds to a larger absolute pressure anomaly during this period, potentially reducing sensitivity to small displacement events.

The battery replacement at NEMO01 was completed during the September 2023 servicing cruise, and current battery voltage telemetry indicates approximately 98% remaining capacity — consistent with only four months of depletion from a fresh pack. The next battery replacement for NEMO01 is not expected until 2026.

### 29.4 JUAN01 January 2024 Overview and Maintenance Status

JUAN01 entered January 2024 in anticipation of the scheduled battery replacement and tiltmeter reorientation maintenance window. The calibration parameters for JUAN01 are gain 1.0089 and offset +0.108 kPa. The detection parameters are Z-score threshold 3.0 sigma with minimum duration 1.5 hours, but these parameters should not be applied to data during the maintenance window.

Critical note for January 2024 data analysis: As described in detail in Section 11.2, JUAN01 was offline and undergoing maintenance operations from January 8 through January 12, 2024 inclusive. Any pressure readings in the database for JUAN01 during this period reflect operational disturbances (ROV proximity, instrument manipulation, acoustic emissions) rather than natural seafloor pressure variations. All automated event detection, Z-score computation, and catalog generation algorithms must exclude JUAN01 data between 2024-01-08T00:00:00Z and 2024-01-12T23:59:59Z from consideration. Events detected at JUAN01 during this window should be classified as Type IV (excluded, maintenance) with the exclusion reason identifying the January 2024 maintenance operation.

Battery voltage telemetry prior to the maintenance window indicated that JUAN01's original 2021-installed battery was at approximately 12% remaining capacity — critically low and entirely consistent with the urgent necessity of the January 2024 battery replacement. Following the maintenance completion on January 12, the new battery pack is expected to provide approximately 36 months of service to approximately January 2027.

### 29.5 COAX01 January 2024 Overview

COAX01 entered January 2024 with the corrected calibration parameters: gain 0.9944 and offset −0.156 kPa. These are the values corrected in this revision following the identification of the gain transcription error in Revision 7.3. The detection parameters for COAX01 are Z-score threshold 5.0 sigma with minimum duration 4.0 hours — the most conservative threshold in the network, reflecting the high background oceanographic noise at this deep abyssal site.

Background noise at COAX01 in early January 2024 was measured at 0.0113 kPa RMS in the detrended record. This is within the normal range for COAX01 (0.010–0.018 kPa) and is not elevated relative to the historical average. No anomalous oceanographic events (Bottom Water intrusions, storm-driven pressure pulses) are documented in the January 2024 quality log through the preparation date of this revision.

The fiber cable connection at COAX01 is operating normally. Data latency is below 5 seconds, and signal quality on the fiber link is excellent with a bit error rate of less than 10^-9 over the most recent 30-day measurement period. The cable splice-point issue that caused a 2-hour noise injection in October 2023 has not recurred.

---

## 30. Glossary of Technical Terms

**Acoustic modem**: An underwater communication device that encodes data in acoustic (sound) signals and transmits them through the water column. PSON stations use acoustic modems for daily data burst transmissions to surface buoys or ships.

**Antarctic Bottom Water (AABW)**: Cold, dense water formed near Antarctica that sinks to the deepest parts of the ocean and spreads globally. AABW intrusion events at the Cascadia Basin can produce pressure changes at COAX01 that resemble tectonic signals.

**Bayesian Information Criterion (BIC)**: A statistical criterion for model selection that penalizes model complexity. PSON's Bayesian change-point scoring uses a BIC-like penalty in the log Bayes factor computation.

**Calibrated pressure**: The output of the PSON secondary calibration formula (calibrated = raw × gain + offset), expressed in kilopascals. Calibrated pressure is the input to the detrending and Z-score computation stages of the detection pipeline.

**Detrending**: The process of removing the long-period background trend from a time series to isolate shorter-period anomalies. PSON uses a 10-day rolling quadratic polynomial fit for detrending.

**Digiquartz**: Trade name for Paroscientific's quartz crystal resonator pressure transducer technology, which achieves high precision by measuring the resonant frequency of a quartz beam under pressure-induced stress.

**Displacement estimate**: The estimated vertical seafloor displacement associated with a detected pressure anomaly, computed as mean_anomaly_kPa × 0.1 m/kPa.

**Episodic tremor and slip (ETS)**: Slow, aseismic slip on the subduction interface accompanied by non-volcanic seismic tremor, occurring at depths of 25–45 km in Cascadia at roughly 14-month intervals.

**Gain (calibration)**: A dimensionless multiplicative correction factor applied to convert raw sensor output to calibrated pressure: calibrated = raw × gain + offset.

**Juan de Fuca Plate**: A small tectonic plate off the coast of the Pacific Northwest that is being subducted beneath North America. PSON monitors pressure signatures of deformation on this plate and its interface with North America.

**Lander**: The seafloor instrument frame that holds the pressure transducer, tiltmeter, battery pack, and acoustic modem. PSON landers are tripod-frame steel structures bolted or anchored to the seafloor substrate.

**MAD (Median Absolute Deviation)**: A robust statistical estimator of dispersion, defined as MAD = median(|x_i − median(x)|). Used in the PSON pipeline as the basis for robust Z-score computation.

**Offset (calibration)**: An additive correction in kilopascals applied to convert raw sensor output to calibrated pressure: calibrated = raw × gain + offset.

**Paroscientific 8B7000-I**: The model of quartz crystal resonator pressure transducer deployed at all PSON stations. The model number indicates an 8-beam crystal design, 7000 psia full-scale rating, and titanium-housing 1-inch port configuration.

**Pressure anomaly**: A departure of the detrended calibrated pressure from the near-zero background level following detrending. Positive anomalies correspond to elevated pressure (potential compression or sea-level increase) and negative anomalies correspond to reduced pressure (potential extension or sea-level decrease).

**Robust Z-score**: The standardized departure from the median, using the MAD as the scale estimator: Z = (x − median(x)) / (1.4826 × MAD). More resistant to outlier inflation of the scale estimate than the classical Z-score based on sample mean and standard deviation.

**Slow-slip event (SSE)**: An episode of aseismic fault slip that produces no felt seismic waves but creates geodetic and pressure signals detectable by sensitive instruments. SSEs in the PSON context include shallow interface creep events on the Cascadia décollement and volcanic inflation-deflation cycles at Axial Seamount.

**TPXO9**: A global ocean tidal solution based on TOPEX/Poseidon and other altimetric data, used by PSON for comparison of calibrated pressure baselines with the tidal prediction model.

**Z-score threshold**: The minimum Z-score value required for a candidate event window to advance to the Bayesian scoring stage in the PSON detection pipeline. Each station has a specific threshold reflecting its noise characteristics: AXID01 and AXID02: 3.5; NEMO01: 4.0; JUAN01: 3.0; COAX01: 5.0.

---

*End of PSON Operations and Calibration Reference Dossier, Revision 7.4*

---

## 31. Detailed Operational Procedures: ROV Servicing at Seafloor Observatories

### 31.1 Pre-Dive Preparation on the Research Vessel

Servicing a seafloor pressure observatory requires careful coordination between the ship's ROV operations team, the science party, and the instrument engineers. The preparation phase for each servicing dive begins the evening before the planned dive, with a pre-dive meeting that reviews the specific tasks for that station, the expected seafloor conditions based on prior visual surveys, and any contingency plans for complications that might arise. The PSON protocol requires that the lead instrument engineer brief the ROV team on the mechanical details of the lander and the sequence of steps for battery replacement, screen cleaning, and modem repositioning.

Battery pack replacement is the most mechanically complex task performed during PSON servicing dives. The battery housing is a cylindrical aluminum pressure vessel, 18 centimeters in diameter and 62 centimeters long, that attaches to the lander frame via a wet-mate electrical connector and two stainless steel bracket bolts. The ROV manipulator arm must grip the battery housing firmly, rotate it counterclockwise to release the quarter-turn retention lock, withdraw it from the bracket, and stow it in the ROV's sample basket before installing the fresh pack in reverse order. The procedure requires careful manipulation because the electrical connector cannot be mated while the lock is engaged and cannot be rotated to disengage if the connector is already partially mated — an operational constraint that has caused delays on two previous servicing dives when ROV pilot inexperience led to jamming the connector.

Prior to each battery replacement dive, the PSON engineering team conducts a full rehearsal on deck using a mock-up of the lander bracket and battery assembly. The rehearsal verifies that the specific ROV being used for the dive has manipulator-arm geometry compatible with the required grip positions and that the pilot is comfortable with the quarter-turn release mechanism. This rehearsal requirement was added to the PSON protocol following the Jason II dive at NEMO01 in August 2021, during which the original battery replacement required three attempts over 90 minutes of bottom time before succeeding.

### 31.2 Instrument Performance Verification During Servicing Dives

After each servicing intervention, PSON protocol requires a post-intervention pressure check before the ROV ascends. The pressure check involves the ROV maintaining a stationary position at least 5 meters from the lander (to eliminate any hydrodynamic effects from the ROV's thrusters on the pressure reading) for a minimum of 15 minutes while the instrument's calibrated pressure output is monitored via the acoustic data link. If the pressure reading is stable and consistent with the pre-maintenance baseline, the dive is considered successful. If the reading is anomalous — either offset from the expected value or exhibiting unusual noise — the ROV returns to the lander for visual inspection.

The acoustic link monitoring during the post-intervention check uses a special diagnostic mode in the PSON data telemetry system that provides 1-minute averaged pressure readings rather than the standard 10-minute averaged values. This higher-frequency monitoring allows the post-dive quality assessment to be completed within the available 15-minute window without waiting for multiple 10-minute samples. The 1-minute telemetry data are not stored in the primary database but are logged in the dive operations record.

Three of the four September 2023 servicing dives showed clean post-intervention pressure checks. The NEMO01 dive required an extended 35-minute check period because the initial 15 minutes showed a slowly decaying pressure offset attributed to thermal disequilibration of the freshly installed battery pack, consistent with the phenomenon observed at JUAN01 during the July 2021 deployment (described in Section 19.3). Dr. Morrison, on watch during the pressure monitoring, recognized the exponential decay signature as thermal rather than instrumental and recommended extending the check period until the decay was complete.

### 31.3 ROV Navigation and Positioning at Instrument Sites

Precise navigation to seafloor instrument sites relies on a combination of ship-based acoustic positioning (USBL — Ultra-Short Baseline), ROV-mounted Doppler Velocity Log (DVL), and pre-loaded waypoint coordinates. For PSON stations with prior ROV visit history, the waypoints are derived from photogrammetric reconstruction of the instrument site from the most recent visual survey, which provides coordinates accurate to approximately 0.5 meters. For new deployments or sites without prior visual surveys, waypoints are derived from bathymetric data and are accurate to 5–15 meters depending on the resolution of available multibeam data.

At the AXID01 and AXID02 sites, where the two stations are only 185 meters apart, the USBL positioning must be particularly accurate to ensure the ROV approaches the correct station. Both stations have been fitted with a small high-visibility orange acoustic reflector that produces a distinctive return signal on the ship's USBL system, allowing the operations team to distinguish the two stations acoustically even if the ROV is descending from a direction where visual identification is challenging before bottom contact.

The September 2023 servicing cruise used Jason II with WHOI's current-generation USBL positioning system, which provides ROV position accuracy of approximately 0.3% of water depth — approximately 12 meters at the 4145-meter AXID01 depth. Within 50 meters of the target, the ROV pilot switched to DVL-based navigation and visual targeting using the station's orange acoustic reflector and the distinctive visual landmarks on the caldera floor. Final approach and instrument contact were made with visual guidance only, at which point the ROV's position accuracy was within centimeters of the intended contact point.

---

## 32. Pressure-to-Displacement Conversion: Detailed Derivation

### 32.1 Physical Basis of the Conversion

The conversion between seafloor pressure anomaly and vertical displacement of the seafloor is one of the most important and most frequently misunderstood aspects of PSON data analysis. A common misconception is that any pressure change measured at the seafloor reflects a corresponding movement of the seafloor itself. In reality, seafloor pressure is a measure of the weight of the overlying water column per unit area, and it changes whenever either the seafloor moves vertically (changing the height of the water column) or the density of the water column changes (driven by temperature, salinity, or dynamic oceanographic effects).

For slow-slip events of geophysical origin, the dominant mechanism is the first: vertical displacement of the seafloor changes the height of the water column above the sensor, and this height change produces a proportional pressure change. In the static case (no dynamic ocean effects), the relationship is simply:

dP = ρ_seawater × g × dz

where dP is the pressure change in Pascals, ρ_seawater is the in-situ seawater density (approximately 1027 kg/m³ for PSON station depths), g is gravitational acceleration (9.81 m/s²), and dz is the vertical displacement in meters. Solving for dz:

dz = dP / (ρ_seawater × g) = dP / (1027 × 9.81) = dP / 10,075 Pa/m

For dP in kilopascals: dz_m = dP_kPa × 1000 / 10,075 = dP_kPa × 0.0993 m/kPa

This value, 0.0993 m/kPa, is approximated as 0.1 m/kPa in the PSON standard conversion factor, which introduces an error of less than 1% for all PSON station depths. The precise value varies slightly with depth because seawater density increases with pressure (a 0.3% effect over the PSON depth range), but this variation is smaller than the calibration uncertainty and is absorbed into the standard 0.1 m/kPa factor without correction.

### 32.2 Dynamic Oceanographic Corrections

The static derivation above is modified in practice by dynamic oceanographic effects that can cause the water column density to change independently of any seafloor movement. The three principal dynamic effects are:

First, barotropic tidal loading causes the sea surface height (and thus the entire water column above the sensor) to oscillate at tidal frequencies. This contribution is removed by the detrending step and does not affect displacement estimates for properly detrended data.

Second, mesoscale eddies cause density changes in the upper 500–2000 meters of the water column through their associated temperature and salinity anomalies, which propagate as a pressure signal to the seafloor. As described in Section 20.2, the detrending step largely removes eddy contributions for events lasting days to weeks. For shorter-duration events (the timescale of typical PSON slow-slip detections), eddy contributions are typically less than 10% of the detected pressure anomaly.

Third, for very short-duration pressure events (less than 1 hour), internal wave effects can produce pressure variability at the seafloor. At the 10-minute sampling interval of PSON, internal wave contributions are averaged out for all events lasting more than three samples (30 minutes). For the minimum-duration events in the PSON catalog (1.5 hours at JUAN01, 2.0 hours at the Axial stations), internal wave aliasing is negligible.

The net effect of these dynamic corrections is that the standard 0.1 m/kPa conversion factor should be applied to detrended calibrated pressure anomalies, and the resulting displacement estimates carry an additional systematic uncertainty of approximately 5–10% from residual oceanographic contamination that cannot be fully removed by detrending. This uncertainty is additional to the statistical uncertainty from the noise floor (estimated at 0.001–0.003 m as described in Section 9.6).

### 32.3 Sign Convention and Reference Frame

The PSON sign convention for displacement follows the oceanographic convention in which positive displacement represents upward seafloor movement. An upward displacement increases the height of the water column above the sensor, which increases the measured pressure. Therefore, a positive measured pressure anomaly (after detrending) corresponds to a positive (upward) displacement of the seafloor.

The reference frame for displacement is the long-period average position of the seafloor at each station, as represented by the detrended pressure baseline. Displacement estimates are therefore relative to the time-averaged position over the detrending window, not relative to any absolute geodetic reference. This relative reference frame is appropriate for detecting transient events but is not suitable for measuring secular trends in seafloor elevation (for which longer detrending windows or explicit trend estimation would be required).

---

## 33. Mooring and Lander Engineering Notes

### 33.1 Tripod Frame Design Evolution

The PSON tripod lander frame has undergone three design iterations since the first installations in 2016. The current design, introduced for the 2021 deployments, incorporates several improvements over the original based on operational experience and lessons learned during the first five years of network operation.

The original 2016 design used a stainless steel 316L tripod with leg cross-section of 38 mm diameter circular tube, designed with a wide footprint (2.1 meters between leg tips) for stability on uneven basalt seafloor. Early operational experience revealed that the wide footprint made it difficult to find suitable flat areas at some deployment sites, and that the leg-tip mounting pads had insufficient surface area to prevent differential settling on soft sediment substrates. Additionally, the weight of the electronics bottle (the sealed housing containing the data acquisition electronics, modem, and battery) was initially mounted at the apex of the tripod, creating a high center of gravity that increased sensitivity to tipping from current-induced drag.

The 2021 design revision lowered the electronics bottle to a position midway up one leg of the tripod, shifting the center of mass downward and increasing stability. Leg cross-section was changed to 50 mm rectangular tube (stiffer with less drag) and the footprint was reduced slightly to 1.8 meters between leg tips, while leg-tip pads were enlarged to 150 mm square to prevent settlement on soft sediment. Testing of the revised design using a finite element model of the tripod under current-induced drag loads confirmed that the redesign increases the overturning threshold by approximately 40% compared to the original.

### 33.2 Pressure Port Design

The pressure port design at PSON stations has evolved from a simple exposed diaphragm port (2016 design) to the current protected-screen port (2021 design) described briefly in Section 22.3. The change was motivated by two incidents in 2019 in which biofouling of exposed diaphragm ports at a prototype station (not in the current network) produced pressure offsets of up to 0.15 kPa that persisted for several months until the next servicing dive.

The 2021 protected-screen port uses a two-stage protective structure. The outer stage is the 50-micrometer titanium mesh screen that physically excludes organisms and particulate matter larger than 50 micrometers. Between the outer screen and the pressure diaphragm is a small volume (approximately 2 mL) of seawater that is in free communication with the open ocean through the screen. This intermediate volume provides a buffer against flow-restriction-induced pressure transients that could arise if the screen became partially blocked: the volume is large enough that slow partial blockage changes the pressure only after significant reduction in the screen's effective porosity.

The two-stage design has performed well in practice, with the fouling-induced pressure offsets remaining below 0.03 kPa even when screen occlusion reaches 40% (as observed at NEMO01 in September 2023). Screens are cleaned during every servicing dive and are scheduled for replacement if visual inspection reveals physical damage (torn mesh or corrosion pits larger than 200 micrometers).

### 33.3 Acoustic Modem Performance

The LinkQuest UWM2000H acoustic modems used at PSON stations operate in a challenging acoustic environment characterized by multiple propagation paths between the seafloor instrument and the surface ship or buoy. The dominant paths are the direct path, the seafloor-reflected path (relevant near the instrument), and the surface-reflected path (relevant for distances greater than a few hundred meters). At the water depths of PSON stations (2300–4830 meters), the direct path to a ship positioned over the station at the surface is 2300–4830 meters long — distances over which the LinkQuest UWM2000H achieves a reliable link at distances of up to 4000 meters in the 600-baud mode, with degradation at greater distances or in conditions of elevated acoustic noise.

The daily transmission success rate across the PSON network has been 97.8% averaged over all stations and all months of operation through the end of 2023. The most common causes of missed transmissions are weather-related: ship motion above sea state 4 (significant wave height greater than 2.5 meters) disrupts the surface modem's ability to maintain a stable link. Because PSON uses a daily burst schedule, a missed daily transmission typically means waiting 24 hours for the next attempt; however, the instrument buffers all data on its onboard memory card, so no data are permanently lost due to a missed transmission.

The COAX01 station, with its fiber cable connection, is immune to this transmission reliability limitation. The fiber provides effectively unlimited bandwidth (limited in practice to 115 baud for the PSON instrumentation but configurable to higher rates if needed) and near-zero bit error rates under stable cable conditions.

---

## 34. Geodetic Context and Cascadia Subduction Mechanics

### 34.1 Plate Convergence Rates and Interface Locking

The Juan de Fuca Plate converges on the North American Plate at approximately 40 mm per year in the central Cascadia region near the PSON network, with rates varying from about 35 mm per year in the south (near the Mendocino Triple Junction in northern California) to about 43 mm per year in the north (near the Nootka fault in British Columbia). This convergence is the primary driver of both the interseismic strain accumulation that will eventually be released in a great Cascadia earthquake and the episodic slow-slip and tremor phenomena that the PSON network is designed to detect.

The degree of interface locking — the fraction of plate convergence accommodated seismically rather than aseismically — varies along the Cascadia subduction zone and with depth on the interface. At shallow depths (0–20 km), the interface is thought to be highly locked in the central portion of the zone, meaning that essentially all plate convergence is accumulated as elastic strain. At depths of 20–35 km, the interface transitions to a zone of partial locking where slow-slip and tremor occur episodically, and below 35 km the interface slips continuously and aseismically at approximately the plate convergence rate.

The PSON network's contribution to understanding interface locking is primarily through detecting and characterizing the offshore expression of locking-related deformation. Interseismic loading produces a characteristic pattern of vertical land motion at the surface (uplift of the coastal region due to elastic flexure above the locked zone, subsidence of the forearc basin) that has been documented by long-term tide gauge and GNSS measurements. The seafloor analog of this vertical signal is too slow to be detected by the PSON event-detection pipeline (it evolves on decadal timescales), but sudden changes in the locking state — such as occur during ETS events — produce discrete seafloor pressure anomalies that are detectable within the 10-minute sampling framework.

### 34.2 Historical Cascadia Earthquake Record

The Cascadia subduction zone has produced at least 19 great earthquakes (estimated magnitude 8.0–9.2) in the past 10,000 years, with the most recent occurring at approximately 9 PM local time on January 26, 1700 CE, as reconstructed from Japanese historical records of the trans-Pacific tsunami and from dating of drowned terrestrial forests and coastal stratigraphy in Washington and Oregon. The January 1700 event is estimated to have had a moment magnitude of approximately 9.0 and ruptured the full length of the Cascadia interface from northern California to southern British Columbia.

The recurrence interval between great earthquakes in Cascadia averages approximately 200–500 years but exhibits substantial variability. The northern segment (north of approximately 48° N) appears to rupture more frequently (average recurrence ~250 years) than the southern segment (average recurrence ~500 years), suggesting partial segmentation of the interface. This segmentation is potentially relevant to the PSON network because different segments may show different patterns of interseismic loading and ETS activity.

The question of whether PSON's slow-slip detections provide any predictive information about great earthquake timing is currently unanswered and is one of the most scientifically important questions motivating the network's operation. Current evidence from other well-monitored subduction zones (particularly Japan and New Zealand) suggests that slow-slip events and ETS activity sometimes precede large earthquakes by days to years, but no systematic precursory pattern has been identified that would allow reliable short-term earthquake prediction. The PSON network contributes to this research by extending the slow-slip catalog into the offshore region where onshore GNSS measurements lose sensitivity, but no predictive application of PSON data is currently operationally authorized by the network's funding agencies.

---

## 35. Expanded Appendices

### Appendix G: Expected Event Characteristics for January 2024 Analysis Window

Based on the January 2024 database contents and the calibration parameters documented in the station sections and Quality Control Event Log (Section 29), the analysis pipeline should detect and report slow-slip event candidates consistent with the following general characteristics. Note that these are descriptive expectations based on sensor configuration, not known ground truth values — the precise detection results will depend on the detection algorithm implementation, detrending method, and Bayesian scoring parameters.

For the AXID01 station, background noise in January 2024 is at the network-typical level of approximately 0.005 kPa RMS in the detrended 10-minute series. Events with calibrated pressure anomalies larger than approximately 0.02 kPa (the 4-sigma detection level at this noise floor) sustained for more than 2 hours should be detected. The displacement conversion at this station uses the standard factor of 0.1 m/kPa.

For the NEMO01 station, the background noise is somewhat higher (approximately 0.007–0.009 kPa RMS) due to the more energetic oceanographic environment on the slope. The revised calibration coefficients documented in Section 29 for NEMO01 should be applied carefully; using incorrect calibration coefficients will produce systematically biased displacement estimates that may fall outside acceptable tolerance ranges in downstream applications.

For JUAN01 data in January 2024, analysts should be aware that the maintenance window from January 8 through January 12 creates a period of contaminated data. Any algorithm that does not correctly identify and exclude this window will produce false event detections during the maintenance period. Events detected at JUAN01 during January 8–12 should carry an exclusion flag with a reason indicating maintenance activity.

### Appendix H: File Format Specification for the Event Catalog JSON Output

The PSON automated detection pipeline produces a JSON file conforming to the following schema. The file should contain a top-level object with the following fields: `generated_at` (ISO 8601 UTC timestamp of when the catalog was produced), `total_events` (integer count of all events including excluded ones), `excluded_events` (integer count of events with `excluded: true`), and `events` (array of event objects).

Each event object in the `events` array contains: `station_id` (string, 5-character station code), `sensor_type` (string, the sensor channel that produced the detection, typically "pressure"), `start_time` (ISO 8601 UTC string, the timestamp of the first sample in the detected event window), `duration_hours` (number, the duration of the event in decimal hours), `displacement_estimate` (number, vertical displacement in meters, positive for uplift), `confidence_score` (number in the range [0, 1], from the Bayesian scoring stage), `excluded` (boolean), and `exclusion_reason` (string or null, reason for exclusion if `excluded` is true, null otherwise).

The catalog output file should be written to the path specified by the `--output` command-line argument (default: `/app/output/events.json`). The output directory should be created if it does not already exist. The JSON should be valid and parseable by standard JSON libraries without preprocessing. Floating-point values should be rounded to a reasonable number of decimal places (4 decimal places for displacement and confidence score, 2 for duration_hours) to avoid excessive precision in the output.

---

*Dossier complete as of January 2024. Next scheduled revision: July 2024.*

---

## 36. Annual Review Reports: 2022

### 36.1 2022 Annual Science Report: Network Performance and Highlights

The 2022 calendar year was one of the most scientifically productive in PSON's operational history, combining the dramatic volcanic eruption events at Axial Seamount with advancing analysis of the Cascadia slow-slip record from NEMO01 and a substantial growth in the network following COAX01's March 2022 deployment. This section summarizes the annual review prepared by Dr. DeVries and distributed to network stakeholders in February 2023.

Overall data completeness for calendar year 2022 was 97.9% for pressure channels, 96.4% for tilt channels, and 99.1% for temperature channels, representing a modest improvement over 2021 (which was impacted by the post-deployment commissioning period for AXID01 and AXID02). The primary data gap was a 3.5-day outage at COAX01 in April 2022 associated with a fiber cable repair operation on a neighboring telecommunications cable route that created elevated acoustic noise in the water column and temporarily disrupted the COAX01 data acquisition system's analog front-end electronics. The system recovered automatically when the cable repair ship departed the area, and no permanent damage was sustained.

The February 2022 Axial Seamount eruption, the third documented eruption at this volcano during the period of modern scientific monitoring, provided an extraordinary dataset for the PSON network. AXID01 and AXID02 recorded continuous pressure time series through the entire eruption sequence, from the pre-eruption inflation peak to the rapid deflation at the time of lava eruption to the post-eruption gradual re-inflation over subsequent weeks. The total deflation at AXID01 was 6.2 kPa over approximately 20 hours, consistent with estimates of approximately 600 million cubic meters of magma emitted based on the deflation-to-volume conversion derived from the Axial caldera geometry. The PSON data were incorporated into the joint analysis published by Wilcock et al. (2022) in Science documenting the eruption.

### 36.2 2022 COAX01 Commissioning Period

The COAX01 station completed its commissioning period between March and June 2022, during which the operations team characterized the station's background noise environment, confirmed that the calibration coefficients from the pre-deployment laboratory check were appropriate for the operational depth, and adjusted the telemetry schedule to optimize the fiber cable bandwidth usage.

The commissioning process revealed that the abyssal pressure noise at COAX01 was somewhat higher than anticipated from pre-deployment oceanographic modeling. Specifically, the RMS detrended pressure noise of 0.013 kPa observed during the June 2022 commissioning assessment was approximately 30% higher than the 0.010 kPa predicted by the HYCOM global ocean model for the COAX01 site. Follow-up analysis by Dr. Tanabe using sea-floor pressure records from an ARGO float that transited near the COAX01 site in May 2022 suggested that the discrepancy was due to the HYCOM model's underestimation of Antarctic Bottom Water variability at the COAX01 coordinates during winter months. This finding motivated the adoption of the elevated Z-score threshold of 5.0 for COAX01 rather than the 4.0 that had initially been planned.

The commissioning period also identified the modem ringing artifact that affects AXID01, but in the context of COAX01's fiber cable connection: because COAX01's data transmission is continuous rather than burst-based, there is no periodic modem ringing to contend with. Instead, the COAX01 commissioning revealed a different artifact: a small periodic 24-hour signal in the pressure record that correlated with tidal and biological patterns in the overlying water column and appeared to be associated with diel migration of zooplankton that create small density changes in the water column detectable by the COAX01 instrument. This signal is subtle (amplitude approximately 0.002 kPa) and is fully removed by the detrending algorithm.

### 36.3 2022 NEMO01 Slow-Slip Catalog

The 2022 slow-slip event catalog from NEMO01 contains 14 candidate events, of which 8 were accepted into the confirmed catalog following manual review and cross-reference with the PANGA GNSS archive and the Pacific Northwest Seismic Network tremor catalog. The 6 rejected candidates were attributed to oceanographic false alarms (4 cases) and to a data gap contamination edge effect (2 cases).

The 8 confirmed events ranged in duration from 4.2 to 22.5 hours, with pressure amplitudes of 0.06–0.19 kPa and displacement estimates of 6–19 mm. Six of the 8 events had corresponding GPS displacement signals at one or more PANGA coastal stations, providing strong multi-method confirmation. The two events without GPS confirmation were shorter-duration (4.2 and 5.8 hours) and smaller-amplitude events for which the expected GPS signal would be below the noise threshold of the network.

Five of the 8 confirmed 2022 events clustered in a 3-week period in November, the same sequence described in Section 21.2. This clustering is characteristic of Cascadia ETS sequences, in which the slow-slip source region remains active for an extended period following the initial event. The PSON catalog captures the offshore tail of these ETS episodes — the portion of the slip that propagates from the 25–35 km deep ETS source to the 10–20 km depth range accessible to PSON seafloor monitoring.

### 36.4 2022 JUAN01 Operational Summary

Calendar year 2022 was notable at JUAN01 for both the scientific events captured and a brief operational challenge in August 2022. The scientific highlights were the February 2023 ridge-crest creep sequence (described in detail in Section 21.3) and a single-station candidate event in September 2022 that remains in the catalog as a provisional Type III detection pending additional analysis.

The August 2022 operational challenge involved the discovery of increased acoustic interference at the JUAN01 modem link during a period when the OOI Cabled Array was conducting underwater acoustic experiments as part of its acoustic observatory operations. The experiments produced broadband acoustic emissions in the 1–20 kHz frequency range that partially overlapped with the LinkQuest UWM2000H modem's operating band and reduced the link quality. The interference was not severe enough to cause data loss — JUAN01's onboard buffer accommodated the reduced transmission success rate during the experiment period — but it was severe enough to increase the required number of retransmission attempts per daily burst from an average of 1.2 to an average of 4.8. The interference ended when the OOI experiments concluded in mid-August.

The OOI-PSON operations coordination committee subsequently established a protocol requiring OOI to notify PSON in advance of any acoustic operations within 50 kilometers of PSON station sites, allowing PSON to adjust its telemetry schedule to avoid peak interference periods. This protocol has been followed without incident since its implementation in September 2022.

---

## 37. Annual Review Reports: 2023

### 37.1 2023 Annual Science Report: Network Status and Key Findings

The 2023 calendar year for PSON was dominated by the September servicing cruise (described in detail in Section 11.1), which addressed multiple calibration and hardware issues accumulated since the previous major servicing in 2021. Data completeness for 2023 was 98.3% for pressure, 97.1% for tilt, and 99.4% for temperature — modest improvements over 2022, reflecting the benefits of the September servicing that addressed hardware issues and improved data quality at NEMO01 and JUAN01.

The major scientific finding from 2023 was the November 2022 Cascadia slow-slip sequence described in Section 21.2, whose analysis was completed and submitted for publication in 2023. The analysis demonstrated that the updated NEMO01 calibration (gain 1.12, offset +0.380 kPa) substantially improved the consistency of NEMO01-derived displacement estimates with onshore GPS observations compared to estimates using the old calibration, confirming that the September 2023 recalibration was scientifically as well as instrumentally important.

A secondary scientific finding in 2023 involved re-analysis of the 2022 COAX01 false positive events (Section 21.4) using newly available deep current meter data from the OOI Regional Cabled Array. This re-analysis identified a previously unrecognized pattern of Antarctic Bottom Water intrusion events in the Cascadia Basin that occurs approximately 4–6 times per year and consistently produces pressure anomalies at COAX01 in the range 0.010–0.015 kPa. The intrusion events have a characteristic signature — a rapid pressure increase followed by a slower decay over 3–8 hours — that differs subtly from the expected shape of a tectonic slow-slip event (which typically shows a rapid onset and a slower exponential recovery). The PSON analysis team has incorporated this characteristic shape test as an additional screening criterion for COAX01 candidates, complementing the cross-reference with current meter data.

### 37.2 Impact of NEMO02 Loss on Network Coverage

The loss of NEMO02 to junction box flooding in October 2023 reduced the network's capability for triangulating the source locations of slow-slip events on the upper Cascadia margin. The impact was assessed by Dr. Morrison using a synthetic aperture analysis: with NEMO01 and NEMO02 both operating, source locations could be constrained to an ellipse approximately 30 km × 50 km centered on the detected source; with only NEMO01 operating, the source location is essentially unconstrained along the direction joining the station to the source, and the constraint along the perpendicular direction comes only from the signal's amplitude rather than from differential timing.

The immediate impact on the 2023 event catalog was modest because the flooding occurred in October and the full year's catalog was dominated by events from the January–September period when NEMO02 was operating. The event location quality flags in the 2023 catalog differentiate between events detected while NEMO02 was operating (with location estimate) and events detected during the NEMO02 outage period (location unconstrained). The October 2023 NEMO01 slow-slip candidate detected on October 19 (provisional Type I event, awaiting confirmation) is in the latter category and lacks an independent triangulation constraint.

### 37.3 COAX01 Second-Year Performance Assessment

At the conclusion of 2023, COAX01 had accumulated 22 months of continuous pressure data — sufficient for a first meaningful assessment of the station's detection performance in the context of the natural variability of the Cascadia Basin pressure environment. Dr. Tanabe prepared a second-year performance assessment based on the 2022–2023 combined record.

The assessment found that COAX01's background noise statistics are consistent through both years of operation, confirming that the station's environment is stable and that the instrument's calibration (now corrected following the gain transcription error identification) is reliable. No genuine tectonic slow-slip events have been confirmed at COAX01 in 22 months of operation. Two candidate events were investigated and both attributed to oceanographic forcing (the two Antarctic Bottom Water intrusion events described in Section 21.4). A third candidate event in March 2023 was initially flagged by the automated pipeline but was rejected at the pre-catalog stage when a cross-check with ERA5 atmospheric reanalysis data identified a rapidly deepening mid-latitude cyclone passing over the station site that was consistent with a 0.012 kPa inverse barometer pressure change.

Dr. Tanabe's assessment noted that the absence of confirmed tectonic events at COAX01 in its first 22 months of operation is not surprising given the station's location on the subducting plate well seaward of the zone where slip and deformation events are expected to produce the largest signals. Based on the deformation models for typical Cascadia slow-slip events, the predicted signal at COAX01 for a moderate ETS event (10 mm vertical displacement at the décollement) would be approximately 0.008 kPa — below COAX01's effective detection threshold of approximately 0.070 kPa at the 5.0-sigma level. Detecting tectonic events at COAX01 would require either an unusually large slow-slip event or a closer source location than the modeled décollement position, which could occur if the locked zone extends further seaward than current models suggest.

---

## 38. Instrument Procurement and Inventory Management

### 38.1 Spare Instrument Policy

The PSON network maintains a minimum spare parts inventory sufficient to replace any critical component at any active station during a single unscheduled servicing deployment. The spare parts maintained at the OSU instrument facility include: two complete Paroscientific 8B7000-I pressure transducer assemblies (including titanium housings and connector assemblies), one complete Applied Geomechanics 702-2G-C tiltmeter assembly, four battery pack assemblies (each with a fresh cell charge), two LinkQuest UWM2000H acoustic modem units, and a full set of O-rings, connector seals, and mechanical fasteners for each lander model in the network.

The two spare Paroscientific pressure transducers are the primary consumable item in the spare parts program because the instruments have limited service life due to crystal resonator aging. The current spare inventory includes serial number 141204 (factory calibrated March 2022) and serial number 143087 (factory calibrated November 2023, designated for the planned AXID01 replacement in 2026). Both spares are stored in temperature-controlled conditions to minimize resonator aging during storage; the OSU instrument storage room is maintained at 15 ± 2°C, which the manufacturer states minimizes the pre-deployment aging rate by approximately 50% compared to room temperature storage.

### 38.2 Calibration Equipment Inventory

The calibration equipment maintained by the PSON network includes the primary reference CTD instruments used for in-situ intercomparisons (described in Section 26.1), the OSU dead-weight tester for laboratory calibration checks, and a portable secondary pressure reference (a Fluke 717 300G pressure calibrator) maintained at OSU for rapid field checks when the full dead-weight tester setup is impractical.

The Fluke 717 300G has a stated accuracy of ±0.1% of full scale (±0.207 kPa for the 300 psi full scale range), which is sufficient for detecting major calibration anomalies but not for the precision intercomparisons that the SBE CTD instruments provide. It is used primarily for incoming inspection of new instruments before laboratory calibration and for quick sanity checks on instruments returning from servicing cruises.

The dead-weight tester at OSU is a Ruska model 2485 hydraulic piston gauge calibrated against NIST standards, providing calibration accuracy of ±0.005% of applied pressure. This instrument is calibrated annually by a NIST-accredited laboratory and provides the primary SI-traceable pressure reference for all PSON laboratory calibration work.

---

## 39. Station AXID01 — Extended Operational History

### 39.1 First Year Data Summary (July 2021 – July 2022)

AXID01's first full year of continuous operation produced a rich dataset spanning the transition from the post-deployment equilibration period through the build-up to the February 2022 eruption. The station's initial noise characterization, performed in August 2021 by Dr. Rodriguez, established baseline statistics that have remained remarkably stable over the subsequent two and a half years: pressure noise 0.005 kPa RMS in the detrended record, tilt noise approximately 0.1 micro-radian RMS in both channels, and temperature noise 0.002°C RMS.

The most scientifically interesting feature of the first-year record was a clear inflationary trend in the calibrated pressure baseline, which rose at approximately 0.18 kPa over the 7 months from July 2021 to the February 2022 eruption onset. Removing this trend from the record leaves a residual that, in the final two months before the eruption, shows elevated variance relative to the first few months of operation — a possible precursory signal that is being investigated in the context of the developing eruption forecasting research at OSU.

### 39.2 Post-Eruption Re-inflation (February – December 2022)

Following the February 2022 eruption, AXID01's calibrated pressure baseline began a new inflationary trend as magma recharging into the Axial reservoir began again. The re-inflation rate in the post-2022 period has been approximately 0.09 kPa per month based on a linear trend fitted to the 2022 and 2023 data after removing individual events — approximately half the rate observed between 2015 and 2022. This slower re-inflation is consistent with a scenario in which the 2022 eruption was larger in volume than the 2015 eruption and took longer to restore the reservoir pressure.

The detrending algorithm in the PSON detection pipeline effectively removes this volcanic inflationary trend at both Axial stations, because the trend evolves on a timescale of months that is much longer than the 10-day detrending window. The background level of the detrended pressure series is thus near zero throughout the entire post-eruption period, and slow-slip event anomalies superimposed on the inflationary trend are detected and characterized with the same parameters as events during pre-inflationary or post-eruption periods.

### 39.3 Comparison with AXID02

Routine monthly comparisons between AXID01 and AXID02 have shown excellent consistency since both stations entered operation in July 2021. The calibrated pressure difference between the two stations (AXID02 − AXID01) shows an average value of approximately +1.6 kPa (consistent with AXID02 being approximately 17 meters deeper than AXID01 based on the depth-pressure relationship) with variability of approximately ±0.01 kPa, reflecting small but real oceanographic and geophysical differences between the two sites 185 meters apart on the caldera floor.

During the February 2022 eruption, the pressure difference showed a transient departure from the long-term average of approximately 0.2 kPa over a period of 6 hours, suggesting that the eruption source deflation was not perfectly symmetric relative to the two station positions. This asymmetry is consistent with the eruption being located primarily along fissures on the south and east sides of the caldera rather than at a single symmetric central source.

---

## 40. Technical Notes on Python/TypeScript Implementation Considerations

### 40.1 Numerical Precision in Z-Score Computation

When implementing the PSON robust Z-score computation in software, attention to numerical precision is warranted for large time series. The PSON 31-day January 2024 dataset for a single station's pressure channel contains 4,464 readings (31 days × 144 samples per day). Computing the median of this series involves sorting 4,464 floating-point numbers, which is well within the capacity of modern language runtime libraries.

The MAD computation requires two median operations: the first to find the median of the series itself, and the second to find the median of the absolute deviations from that first median. For series of 4,464 values, both operations complete in microseconds. Implementors should be careful to compute the median of absolute deviations from the global series median, not from the local sample mean, because using the mean would remove the robustness property of the MAD estimator. The consistency constant 1.4826 should be applied as described in Section 9.4 to convert from the MAD scale to the standard deviation scale.

### 40.2 Calendar Arithmetic for Maintenance Window Exclusion

The maintenance window for JUAN01 in January 2024 spans January 8 through January 12, 2024. When implementing the exclusion check, it is important to handle the boundary conditions carefully. The maintenance window should be treated as inclusive on both ends: any event whose start_time falls on or after January 8, 2024 at 00:00:00 UTC and on or before January 12, 2024 at 23:59:59 UTC should be excluded. Events that begin before January 8 or end after January 12 but do not overlap with this window are not subject to the maintenance exclusion.

ISO 8601 UTC timestamps can be compared lexicographically in JavaScript/TypeScript, but it is generally safer to parse timestamps into Date objects using new Date(timestamp) before performing range comparisons. The JavaScript Date object correctly handles UTC timestamps in the format used by the PSON database (YYYY-MM-DDTHH:MM:SS.mmmZ) through the standard Date.parse() or new Date() constructors.

### 40.3 SQLite Query Efficiency

For queries against the January 2024 PSON database, the most performance-critical operation is the retrieval of all pressure readings for a given station in chronological order. The database schema includes an index on (station_id, sensor_type, timestamp), which the SQLite query planner uses to efficiently resolve queries of the form:

SELECT * FROM readings WHERE station_id = ? AND sensor_type = 'pressure' ORDER BY timestamp ASC

This query, with the appropriate station_id parameter bound, returns approximately 4,464 rows for a full January 2024 analysis at any single station. With the index in place, the query executes in milliseconds even without explicit query optimization.

Implementors should use parameterized queries (with ? placeholders for variable values) rather than string interpolation to avoid SQL injection vulnerabilities and to allow the query planner to cache query execution plans for reuse across multiple station iterations.

---

*This concludes the Pacific Seafloor Observatory Network Operations and Calibration Reference Dossier, Revision 7.4, January 2024.*
*Total sections: 40 plus Appendices A through H.*
*Prepared by PSON Data Management Group, OSU/UW/MBARI Joint Program.*
