---
layout: post
title: "On Consistency and Durability"
date: 2013-12-10
comments: false
---

In case you've missed it, there's been a [great
discussion](https://news.ycombinator.com/item?id=6878005) about
consistency, availability, and durability on the [Redis mailing
list](https://groups.google.com/forum/#!topic/redis-db/Oazt2k7Lzz4)
and [Twitter](https://twitter.com/kellabyte/status/410224523602960385)
over the past few days. I wanted to weigh in and specifically address
[antirez's point](https://news.ycombinator.com/item?id=6880574) that

> While CAP and durability are orthogonal they are very related in actual systems....

---

We can effectively cast all statements about availability and
consistency into the form:

> If operations can contact AF of N correct replicas, the system provides a guaranteed response that is correct with respect to semantics S.

Availability is all about the precondition (AF of N): under what
conditions is a safe response guaranteed? Gilbert and Lynch's [proof
of the CAP
theorem](http://lpd.epfl.ch/sgilbert/pubs/BrewersConjecture-SigAct.pdf),
shows that when S means
[linearizability](http://en.wikipedia.org/wiki/Linearizability) and N
is greater than 1, AF cannot equal 1. In fact, most
[implementations](http://webee.technion.ac.il/uploads/file/publication/731.pdf)
of linearizability use a notion of majorities to pick AF = (N+1)/2.

---

Now, let's consider statements about durability:

> The effects of operations will survive DF fail-stop server failures.

To survive DF failures, we need to contact DF+1 servers. Therefore, we
can provide availability and durability only when enough servers are
online and reachable.

---

As stated, two concepts are remarkably similar, but there's an
important difference. For semantics like linearizability, AF is
typically a function of N and grows with replication factor. In
contrast, DF is typically constant and independent of replication
factor.

This brings us to antirez's point. When N=3 and we want writes to
survive one server failure, majority quorums require AF=2 and
durability also requires DF=2; they're the same! When we want higher
durability without having to contact all servers, N=5 with DF=3 is a
reasonable choice, and, again, durability matches majority quorum
size. For large replication factors, N=100, the difference grows: we
can still get DF=3, while majority quorums require AF=51. But, in
practice, replication factors are often small, so the preconditions
for availability when maintaining both durability and consistency are
often equivalent.

It's worth noting that AF=1 and DF=1 *is* an option, and it's
[fast](http://cs-www.cs.yale.edu/homes/dna/papers/abadi-pacelc.pdf),
but it will preclude durability in the event of server failures and
also disallows linearizable semantics in the event that you have
multiple active replicas (N > 2).

The above analysis doesn't take into account reads, which, in weakly
consistent systems, can contact any non-failing replica, but I think
this sheds some light on the discussion.        