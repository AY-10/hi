# TRADEOFFS

1. I did not build file upload parsers for every source format. The demo seeds realistic rows directly so the prototype can demonstrate normalization and review behavior without spending the whole assignment on CSV and PDF edge cases.

2. I did not build authentication or row-level permissions. The assignment is about ingestion judgment and analyst sign-off, so I kept the control plane simple and left identity as a deployment concern.

3. I did not build a full emissions factor service. The prototype uses a small built-in factor table so the app can explain how a normalized row becomes a reviewable carbon value.
