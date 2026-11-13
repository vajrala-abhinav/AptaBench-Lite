# Scientific policy: lite-seq-v1.0-conservative

Normative authority: master design §§4–14 and §24. This file documents operational
choices; it does not introduce a biological identity classifier or validated confidence.

- Significant gold only, linked attempted papers. Separate type and presence columns are
  supported. Invalid significant references remain visible but leave the scoreable G.
- Case/whitespace and explicitly paired 5′/3′ labels only. Raw text and offsets remain.
  Literal ambiguous IUPAC and mixed T/U strings are retained and require identity review.
  No wildcard, reverse, reverse-complement, transcription or chemical-label repair.
- Strict canonical duplicate grouping within each paper; never tolerance-based deletion.
  Default E counts unique canonical predictions. If golds share that canonical string,
  retain available original extractor item capacity and flag identity conflict; never
  claim the items identify individual golds automatically. Contradictory names in a
  duplicate group prevent automatic use; all member identities remain in the audit.
- Unique uncontradicted exact-whole anchors precede contextual assignment. Every
  remaining same-paper gold × logical-extractor edge is retained, including failures.
  For inspectability, anchored/preempted edges are also cached and tagged separately;
  they cannot compete with locked endpoints.
- Shared unit-cost global and full-gold fitting DP: free extractor prefix/suffix,
  penalized internal skips and every missing gold base. Deterministic traceback prefers
  distance, then more matching bases, then diagonal/deletion/insertion. All equally
  minimal fitting intervals are counted, independent of the chosen display trace.
- Exact integer B(L)=max(1,min(4,isqrt(L//9))). Correctness uses distance, not rounded %.
- Sequence-local strict-name agreement supports an edge; disagreement is a material
  conflict. A name alone or an out-of-budget comparison never auto-associates.
  Notes count as names only with explicit `name:`, `aptamer name:` or equivalent `=`
  syntax. An independent worksheet list is not used as item identity evidence.
- Exact repeated motifs, multiple optimal fits, contradictory names, identical gold
  identity and ambiguous alphabets use conservative review fallback. No hard minimum
  length, entropy cutoff, confidence percentage or arbitrary completion margin is used.
  Unique exact-whole anchors are still allowed for short sequences.
- Paper-wide exact assignment allows unmatched dummy nodes. Among viable remaining
  edges the lexicographic priorities are: number of explicit supported names, number
  of compatible associations, sum of gold-relative core completion; in contested
  components only, sum of clamped gold-relative global completion. These are exact
  rational/integer categories, not calibrated probabilities. Contextual equivalence
  is tested by forbidding each selected edge once. Only edges fixed across optima
  may be accepted; others stop at review. Source IDs sort display only.
- Global completion cannot veto a uniquely viable core fit. It only ranks actual
  competition. Ties and material independent conflicts abstain.
- The same immutable associations receive four stored pass flags and eight metric views.
  All: TP=T, FP=E−T, FN=G−T. Matched: correctness=T/M, with recovery=T/G. No denominator
  shrinking for pending review. No blind count balancing when E≥G.
- Human review is an identity overlay. It cannot edit source bases or change distances.
  Incorrect confirmed pairs remain failed nucleotide values. Both automatic and effective
  results are exported; effective completion can mean reviewed missing, not recovered.

Research-owner review is needed before relaxing the qualitative fallback in §24 or
adopting a different lexicographic hierarchy. The current conservative behavior may
leave genuine matches unresolved; no claim of guaranteed biological identity is made.
Pool/Kd, modification-aware bases, wildcard/RC matching and shared hosting are deferred.
