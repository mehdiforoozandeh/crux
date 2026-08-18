# h1 — pooled vs linear readout, held-out split

The claim-directed numbers are in `metrics.txt`: the pooled readout beats the linear one by
0.0276 mIoU on average, and by at least 0.02 on all five seeds.

The control is in `shuffled_labels.txt`, and it did not pass. Both arms score far above
chance on shuffled labels, so the held-out split leaks into training and neither arm's
number means what it was supposed to mean.
