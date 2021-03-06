---
layout: post
title: "Safety and liveness: Eventual consistency is not safe"
date: 2012-03-27
---

*tl;dr: Eventual consistency is a liveness property---not a safety property---and is trivially satisfiable by itself. Liveness and safety properties should be taken together.*

Safety and liveness are two important kinds of properties provided by [all distributed systems](http://pi1.informatik.uni-mannheim.de/filepool/teaching/dependablesystems-2007/PDS_20070306.pdf). Informally, safety guarantees promise that nothing bad happens, while liveness guarantees promise that something good eventually happens. Every distributed system makes some form of safety and liveness guarantees, and some are stronger than others. For example, [atomic consistency](http://en.wikipedia.org/wiki/Linearizability) guarantees that operations will appear to happen instantaneously across the system (safety) but operations won't always succeed in the presence of network partitions (liveness, in the form of availability).

Many of today's distributed systems promise [eventual consistency](http://en.wikipedia.org/wiki/Eventual_consistency): after some period of time, all participants in the system agree on the same value. This is a useful property: good things will eventually happen without the need for intervention, even in the presence of partitions. However, under our definitions of safety and liveness, eventual consistency only provides liveness guarantees, not safety: Which value is eventually chosen? What values may be returned before participants "eventually" agree?

As [recent work from UT Austin](http://www.cs.utexas.edu/users/princem/papers/cac-tr.pdf) points out, it's easy to satisfy liveness without being useful. If all replicas  always return the initial state, the system is eventually consistent. If all replicas return the value 42 in response to every request (even if you didn't write the value of 42), the system is eventually consistent. If replicas accept every thousandth write, the system is eventually consistent. These guarantees are somehow not what we would like, but they satisfy our definition of eventual consistency. Moreover, as the authors explain, accepting more read/write combinations doesn't necessarily translate to *stronger consistency*.  We'd like some notion of *convergence* that captures both agreement on a common shared state and exchanging of writes.<sup><a class="no-decorate" href="#strengthnote">1</a></sup>

Today's eventually consistent systems do provide some form of safety properties, even if they don't say so explicitly. For instance, in Riak, Cassandra, and DynamoDB, timestamp ordering is often used to decide which version of a data item to keep. Moreover, these data stores won't return any values you haven't written to them, and replicas will converge to the last written value for each key. In short, many "eventually consistent" stores really offer something like "eventually last-writer-wins, and read-the-last-observed-value in the meantime" consistency. This is both more descriptive and more useful than a vanilla "eventual consistency" guarantee.<sup><a class="no-decorate" href="#vendornote">2</a></sup>

It's worth noting that safety without convergence also leads to problems. Read-your-writes, PRAM/monotonic writes, and causal consistency guarantees are trivially achievable using only local storage and no communication: simply keep a local copy of every key that you update and read from for every operation. This is not a convergent implementation. However, it satisfies [each of these consistency models](http://www.allthingsdistributed.com/2008/12/eventually_consistent.html) because they make safety but not liveness guarantees. If we were to add in our liveness requirement of convergence, our implementation would have to propagate writes between replicas.

Next time someone tells you their system is "eventually consistent," ask them two questions: What versions of a data item can be returned at any time? What version will the system eventually choose to return? And remember: consider safety and liveness properties together. Otherwise, you probably have a trivially satisfiable requirement.

*This post was influenced in large part by discussions with [Ali Ghodsi](http://www.sics.se/~ali/), [Joe Hellerstein](http://db.cs.berkeley.edu/jmh/), and [Ion Stoica](http://www.cs.berkeley.edu/~istoica/).*

<hr>

<div id="footnotetitle">Footnotes</div>

<div class="footnote" id="strengthnote"><a class="no-decorate" href="#strengthnote">[1]</a> Eventual convergence is likely the strongest convergence property we can guarantee given unbounded partition durations. Any system guaranteeing non-trivial convergence within a fixed amount of time would violate its liveness guarantees if partitioned for a longer period of time.</div>

<div class="footnote" id="vendornote"><a class="no-decorate" href="#strengthnote">[2]</a> In their technical documentation, vendors are usually forthcoming about these details, though they can be difficult to pick out. However, in promotional material and especially when making superficial comparisons, these distinctions are often omitted or glossed over.</div>
