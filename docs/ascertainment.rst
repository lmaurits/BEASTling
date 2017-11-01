========================
Ascertainment correction
========================

Ascertainment correction refers to conditioning likelihood calculations on the
fact that certain patterns of data are guaranteed not to occur in the data for
some reason.  If ascertainment correction is not peformed in an analysis where
some kinds of data are guaranteed not to occur, BEAST will think the absence of
that kind of data is simply due to it never having evolved, and this can bias
e.g. the timing of trees.

Ascertainment correction is relevant to BEASTling analyses in two cases.
BEASTling tries to automatically do "the right thing" when it can, but the
interaction between different considerations can be confusing, so this page
attempts to lay everything out clearly.

Constant feature ascertainment correction
-----------------------------------------

One is the case of constant features.  It is common to remove constant features
from analyses because they cannot inform the tree topology or timing.  E.g. if
all the languages in your dataset use SOV word order, there is no point
including this because it can't help to separate out clades.  In fact, if you
are using any non-binary substitution model (like LewisMk or BSVS), you have no
choice but to remove it, because these models infer their state space from
looking at the data, and they do not make any sense for a state space of just
one value.  BEASTling will remove these features for you automatically and there
is no way to override this, as it makes no sense.  If you are using a binary
substitution model, like BinaryCovarion, it is actually possible to leave
constant features in.  The model defines its own state space, so even if some
feature only has values of 0 in your dataset, BEAST knows that the alternative
value 1 exists.  BEASTling will still remove constant features by default to
make your anlyses smaller and faster, but if in this case you can override this
behaviour by setting ``remove_constant_features=False`` in the ``[model]``
section.  You might like to do this if you are inferring per-feature rates, for
instance.

You can explicitly tell BEASTling to include ascertainment correction for the
absence of constant features (or not) by setting ``ascertained`` to ``True`` or
``False`` in a ``[model]`` section.  BEASTling will do as it is told.  However,
if you remain silent, the following will happen.

Since ascertainment correction only affects the timing of the inferred trees, if
you have not placed any time calibrations in your analysis, BEASTling will
assume you are primarily interested in tree topology and will not perform
ascertainment correction.  Feel free to tell it otherwise!

If you *have* included time calibrations, BEASTling will include constant
feature ascetainment correction if it thinks its needs to, according to the
following logic.

If you are using a substitution model which does not define its own statespace,
then constant features make no sense and will be forcibly removed from the
analysis, so you definitely need the correction and it will be included.

What if you are using a substitution model which *does* define its own
statespace, such as BinaryCovarion?

If BEASTling finds constant features in your dataset and removes them (as is its
default behaviour), then you definitely need the correction and it will be
included.  If you use ``remove_constant_features=False`` and BEASTling notices
that constant features do in fact exist and have been let through into the
anslysis, then you definitely do *not* need the correction and so it will not be
included.

Where things get a little tricky is when there are no constant features in your
dataset.  If BEASTling hasn't seen any constant features for itself (whether it
subsequently removed them or not) it can't make an educated guess as to whether
or not the ascertainment correction is necessary.  In this case, BEASTling errs
on the side of caution and enables the correction based on the developers'
beliefs that most data sources without constant features *probably* are
deliberately collected in such a way as to exclude constant features.  If this
is not true in your case and you want to disable the correction, use
``ascertained=False``.

Binarised data ascertainment correction
---------------------------------------

The second case of ascertainment correction relevant to BEASTling is
ascertainment correction for binarised data.  It is common to model lexical
evolution by treating each cognate class associated with a particular meaning
slot as an indendent binary feature, and setting a datapoint to 1 or 0 depending
upon whether a language's word for that meaning does or does not belong to the
corresponding cognate class.  A consequence of this representation is that your
data will never contain a feature whose value is 0 for every language, because
every cognate class must have at least one word belonging to it.

BEASTling offers less control over whether or not this kind of ascertainment
correction is performed (this is purely for historical/backwared compatibility
reasons and may change in future).  Regardless of whether or not you have any
timing calibrations in place, the correction will be performed if BEASTling
believes that your data is in this binarised format.  This is true if:

* BEASTling has done the binarisation for you
* You have done the binarisation yourself and used ``binarised=True`` to inform
  BEASTling of this fact.

Otherwise it will not be performed.
