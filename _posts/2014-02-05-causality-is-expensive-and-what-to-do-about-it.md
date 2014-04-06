---
layout: post 
title: "Causality is expensive (and what to do about it)"
date: 2014-02-05 
comments: false 
---

In this post, I briefly motivate the use of causality in distributed
systems, discuss (likely) fundamental lower bounds on metadata
overheads required to capture it, and discuss four strategies for
circumventing these overheads.

### Why care about causality?

In 1978, Leslie Lamport introduced the important concept of [partial
ordering in distributed
systems](http://www.stanford.edu/class/cs240/readings/lamport.pdf):
given a partial view over global system state, how can we safely say
whether a particular event "happens before" another? Instead of
relying on a total order (e.g., using synchronized clocks) to order
events, Lamport's proposed ["happens-before"
relation](http://en.wikipedia.org/wiki/Happened-before) captures
dependencies between events as a [partial
order](http://book.mixu.net/distsys/time.html): "happens-before"
reflects the order of events within each process as well as the order
of events across processes, captured via message channels. This
formulation conveniently means that reasoning about "happens-before"
does not require synchronous coordination between processes and also
captures the possibility that two events may be completely independent
of one another (i.e., are concurrent; just like [light
cones](http://en.wikipedia.org/wiki/Light_cone) in the real
world). Accordingly, "happens-before" is a powerful concept and forms
the basis of *causality* in distributed systems, which is used in many
contexts:

   1. Distributed snapshot algorithms (e.g., [consistent
  cuts](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.63.4399&rep=rep1&type=pdf))
  and global predicate detection algorithms typically leverage causal
  ordering for efficient execution (e.g., enable consistent snapshots
  without forcing processes to pause). This is particularly useful in
  debugging.

   2. [Version vectors](http://en.wikipedia.org/wiki/Version_vector)
  are used in databases like Dynamo, Riak, and Voldemort to track
  concurrent updates to data and [manage update
  conflicts](http://zoo.cs.yale.edu/classes/cs422/2013/bib/terry95managing.pdf)
  without fast-path synchronization between replicas.

   3. [Causal
  consistency](http://en.wikipedia.org/wiki/Causal_consistency) and
  [causal
  broadcast](http://www.info.ucl.ac.be/courses/SINF2345/2010-2011/slides/5b-causal-broadcast-hand.pdf)
  provide databases and messaging systems with ordering guarantees
  that respect Lamport's "happens-before" relation. This means, for
  example, that replies on Twitter won't be seen without their parent
  Tweets. These two use cases in particular have recently seen a
  resurgence of interest in the research community.

As a theoretical construct and, increasingly, in real-world
distributed systems, causality is important. I'll defer a full
description and discussion of causality to the expansive literature
([here's](http://aqualab.cs.northwestern.edu/component/attachments/download/302)
a survey, and [here's my
favorite](http://www.vs.inf.ethz.ch/publ/papers/holygrail.pdf)---check
out that subtitle!). Instead, I want to ask a specific question: what
does causality cost?

### Causality is expensive

To use causal ordering, we need some way to *capture* it via a data
structure or other piece of information. There are a variety of
techniques for doing so in the literature that you may have heard of,
like [vector clocks](http://en.wikipedia.org/wiki/Vector_clock) (note
that the related [Lamport
clocks](http://en.wikipedia.org/wiki/Lamport_timestamps) don't allow
us to distinguish between "concurrent" and "earlier" events). If
you're familiar with vector clocks, you'll know that each process in
the system requires a position in the data structure; this means that,
with N processes, each vector clock takes up O(N) space.

This leads to a tough question: how much space is *required* in order
to capture causality? This is a difficult question to answer, but it's
fascinating to think about and has serious implications for our above
use cases. Fortunately, Bernadette Charron-Bost thought seriously
about this problem, and, in 1991, published [a surprising
result](http://dl.acm.org/citation.cfm?id=117606); the actual paper is
fairly hairy, but Schwarz and Mattern [summarize
well](http://www.vs.inf.ethz.ch/publ/papers/holygrail.pdf):

> Is there a way to find a "better" timestamping algorithm based on
> smaller time vectors which truly characterizes causality? As it
> seems, the answer is negative. Charron-Bost showed...that causality
> can be characterized only by vector timestamps of size N.

Wow. Charron-Bost's result seems to imply that we can't use less than
O(N) metadata! For small numbers of processes, this isn't so bad, but,
if we scale to hundreds or thousands of nodes, *each* message (or, in
a database, operation) is going to require a lot of metadata. Schwarz
and Mattern (do you recognize Mattern from earlier?) continue:

> It is not immediately evident that --- for a more sophisticated type
>  of vector order than < --- a smaller vector could not suffice to
>  characterize causality, although the result of Charron-Bost seems to
>  indicate that this is rather unlikely...A definite theorem about the
>  size of vector clocks would require some statement about the minimum
>  amount of information that has to be contained in timestamps in
>  order to define a partial order of dimension N on them. Finding
>  such an information theoretical proof is still an open problem.

So, we don't have a definitive proof, but, in all likelihood, we're
not going to do better. Moreover, in the now 23 years following this
result, we haven't seen anyone do better.

Intuitively, I think of the lower bound as follows: if I'm a process,
and I want to perform an event, I need some way to distinguish my new
event from all of the prior events that I've performed. This hints
that I'll need some sort of unique marker for my event---as in a
vector clock, I can use a local timestamp that I increment on every
event (which requires O(log(events)) space). Now, if *every* other
process simultaneously wants to perform a new event, then we'll
collectively need N timestamps. We can't coalesce these timestamps,
since they're due to unique events, so this puts us at (at least) O(N)
metadata! Some [recent
results](http://research.microsoft.com/pubs/201602/replDataTypesPOPL13-complete.pdf)
from Microsoft Research and the CRDT team show similar bounds for
vector-based data structures.

### ...and what to do about it

There are many optimizations that reduce the overhead of causal
tracking in the best case, but these [worst-case
overheads](http://en.wikipedia.org/wiki/Murphy's_law) are too costly
for many modern services running at scale. (Perhaps surprisingly, many
modern implementations are even more expensive, with worst-case
metadata overheads that are linear in the number of events or the
number of keys in a database.) If you're interested, we wrote a paper
a while ago about [how bad this overhead can
become](http://www.bailis.org/papers/explicit-socc2012.pdf)
([voiceover](http://vimeo.com/51578973)) for causally consistent
databases backing modern internet services.

Can we do anything to avoid these overheads?

  1. *Restrict the set of participants:* To reduce the O(N) factor, we
  can reduce N, or the number of processes across which we track
  causal information. For example, if we're building a distributed
  database, we can simply track causality across replicas of a each
  data item instead of causality across all servers. This sacrifices
  causal guarantees across data items but allows us to detect update
  conflicts for a single data item and is exactly the strategy adopted
  by [version
  vectors](http://en.wikipedia.org/wiki/Version_vector). In most
  systems, the number of replicas for an item is much smaller than the
  number of servers in the system (e.g., 3 vs. 100), so this is a
  substantial reduction *in practice*. (Carlos Baquero has a [good
  post](http://haslab.wordpress.com/2011/07/08/version-vectors-are-not-vector-clocks/)
  on this distinction.)

  2. *Explicitly specify relevant relationships:* The above discussion
  assumes that all events matter equally; in practice, this isn't
  necessarily the case. On Twitter, when a user posts a reply to a
  Tweet, the causal relationship between the reply and the parent
  Tweet is---from a UX perspective---more important than the
  relationship between all of the Tweets the user read at login and
  her new reply. Effectively, if traditional forms of causality (i.e.,
  *potential causality*) treat all *possible* (transitive) influences
  equally, what if we could *explicitly* specify which partial orders
  matter? In our Twitter example, tracking this *explicit causality*
  would only require a metadata overhead of O(1) for the "reply-to"
  relationship. The trade-off is that (like foreign key dependencies
  in database systems), the user now has to specify her causal
  dependencies manually at write time; our
  [paper](http://www.bailis.org/papers/explicit-socc2012.pdf) I
  mentioned earlier describes this strategy in greater detail.

  3. *Reduce availability:* The problem with reducing the set of
  participants or using explicit causality is that we will necessarily
  throw away some causal dependencies. The upshot is that we were able
  to to reduce metadata while preserving availability. An alternative
  strategy is to attempt to compress causality by restricting
  availability: if we bound the number of processes that can
  simultaneously perform operations to a constant factor K, we only
  need K entries in our vector at any given time (i.e., to perform an
  operation, a process must "reserve" a spot in the vector, then
  "catch up" to the current vector position in the causal
  history---by, say, processing the events created and received by the
  prior occupant of the position).  Under this strategy, metadata size
  determines maximum concurrency; in the limit, with K=1, we have a
  total order on events (close---if not identical
  to---[linearizability](http://en.wikipedia.org/wiki/Linearizability)). With
  this strategy, we've traded metadata by sacrificing availability and
  forcing some processes to effectively "share" causal dependencies.

  4. *Drop happens-before entirely:* If we don't want to suffer
  metadata overheads, require programmer intervention, or sacrifice
  availability, we can always use a weaker partial order (i.e., weaker
  but still available model). For example, if, in a database, we
  simply want each user to read her writes, we don't (necessarily)
  need any metadata and can simply use [sticky routing
  policies](http://www.bailis.org/blog/stickiness-and-client-server-session-guarantees/). Vanilla
  [eventual
  consistency](http://www.bailis.org/blog/safety-and-liveness-eventual-consistency-is-not-safe/)
  is even cheaper. Of course, this
  [strategy](http://www.datastax.com/dev/blog/why-cassandra-doesnt-need-vector-clocks)
  can [clearly
  compromise](http://aphyr.com/posts/294-call-me-maybe-cassandra/)
  application consistency because we lose the ability to distinguish
  between concurrent writes and overwrites to the same item, but, on
  the plus side, it doesn't get much cheaper!

  It's also important to remember that, regardless of the model we
  choose, if we want true "availability", we necessarily [lose the
  ability to make many useful
  guarantees](http://www.bailis.org/papers/hat-vldb2014.pdf), like
  preventing concurrent updates. There's no free lunch, but, given
  that not all "weak" models are created equal (at least in terms of
  metadata cost), sometimes it makes sense to drop full causal
  ordering across all events and all processes and settle for
  enforcing a less costly alternative.

### Takeaways

Causality is an immensely powerful concept in distributed systems, but
it's unlikely that we'll discover a more compact, sub-linear
representation that is sufficient to characterize it. I have no doubt
that causality will remain important for debugging and reasoning about
global states of distributed computations and am excited by the recent
work in causally consistent distributed systems (full disclosure: I
spent [some time on
this](http://www.bailis.org/papers/bolton-sigmod2013.pdf) earlier in
my Ph.D.). As researchers, it's our job to push the envelope, and
understanding the compromises required in light of the (likely)
fundamental trade-offs I've described is a worthwhile
exercise. However, given the worst-case overheads of causality
tracking---at least in real-world deployments---and lack of a more
compact counterexample, I'm more bullish on the four alternatives I've
outlined.
