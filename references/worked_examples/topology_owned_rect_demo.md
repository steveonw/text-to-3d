# Topology-Owned Rect Perimeter Demo

## DSL
```text
object fence
  label yard_edge
  roles barrier boundary
  mode rect_perimeter
  importance primary

object gate
  label front_gate
  roles gate_opening gate_frame
  target yard_edge
  socket opening
  facing south
  importance primary

object fountain
  label shrine_center
  inside yard_edge
  importance primary

object table
  label center_table
  inside yard_edge
  importance secondary

object torch
  label gate_torches
  count 2
  roles marker
  target yard_edge
  socket face
  near front_gate

object rubble
  label clutter
  count 3
  mode scatter
  inside yard_edge

object road
  label approach
  mode line
  target front_gate
```

## ASCII
```text
····················
····················
····················
····················
····················
····················
····················
····················
··········HHHHHHHH··
··········H······H··
··········H······H··
··········H··T···H··
··········H···FF·H··
··········H···FF·H··
··········H······H··
··········HHH·GHHH··
············T··T····
····················
····················

Legend: ==road F=fountain G=gate H=fence T=torch ░=MA
```

## Notes
- `yard_edge` is emitted directly from topology, not reconstructed from legacy perimeter output.
- `front_gate` is cut into the south side using a true topology opening.
- `gate_torches` are re-seated from authoritative topology slots, with near-bias and symmetry preference.
- `center_table` is handled as a true center placement via runtime nudge logic, not a motif approximation.
