No rush. When you are back: the fix is the 20-line patch described in my last comment (`MinSumBPDecoder::new` and `compute_hard_decision`). On the d = 5 leaked-qubit DEMs it brings the logical error rate from 12.84 % to 1.24 % (ancilla) and from 5.60 % to 1.26 % (data qubit). It only really covers F32/F64 so far.

If it is easier for you, I can open a PR with that change plus a regression test on a leaked-qubit DEM. For transparency: this analysis and the patch were written with AI assistance, in case that matters for how you want to take the code.
