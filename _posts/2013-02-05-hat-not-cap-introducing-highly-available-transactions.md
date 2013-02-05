---
layout: post
title: "HAT, not CAP: Introducing Highly Available Transactions"
date: 2013-02-05
comments: false
---

*tl;dr: [Highly Available
 Transactions](http://arxiv.org/pdf/1302.0309.pdf) show it's
 possible to achieve many of the transactional guarantees of today's
 databases without sacrificing high availability and low latency.*

#### CAP and ACID

Distributed systems designers face hard trade-offs between factors
like latency, availability, and consistency. Perhaps most famously,
the [CAP Theorem](http://en.wikipedia.org/wiki/CAP_theorem) dictates
that it is impossible to achieve "consistency" while remaining
available in the presence of network and system partitions.<sup><a
class="no-decorate" href="#cap-note">1</a></sup> Further, even without
partitions, there is [a trade-off between response time and
consistency](http://dbmsmusings.blogspot.com/2010/04/problems-with-cap-and-yahoos-little.html). These
fundamental limitations mean distributed databases can't have it all,
and the limitations aren't simply theoretical: across datacenters, the
penalties for strong consistency are on the order of [hundreds of
milliseconds](http://highscalability.com/numbers-everyone-should-know)
(compared to single-digit latencies for weak consistency) and, in
general, unavailability takes the form of a
[404](http://en.wikipedia.org/wiki/HTTP_404) or [Fail
Whale](http://www.whatisfailwhale.info/) on a website. Over twelve
years after Eric Brewer [first stated the CAP
Theorem](http://www.eecs.berkeley.edu/~brewer/cs262b-2004/PODC-keynote.pdf)
(and after [decades of building distributed database
systems](http://www.rfc-editor.org/rfc/rfc677.txt)), data store
designers have taken CAP to heart, some choosing consistency and
others choosing availability and low latency.

While the CAP Theorem is fairly well understood, the relationship
between CAP and [ACID transactions](http://en.wikipedia.org/wiki/ACID)
is not. If we consider the current lack of highly available systems
providing arbitrary multi-object operations with ACID-like semantics,
it appears that CAP and transactions are incompatible. This is partly
due to the historical design of distributed database systems, which
typically chose consistency over high availability. Standard database
techniques like [two-phase
locking](http://en.wikipedia.org/wiki/Two-phase_locking) and
[multi-version concurrency
control](http://research.microsoft.com/en-us/people/philbe/chapter4.pdf)
do not typically perform well in the event of partial failure, and the
master-based (i.e., master-per-shard) and overlapping quorum-based
techniques often adopted by [many distributed database
designs](http://research.microsoft.com/en-us/people/philbe/chapter8.pdf)
are similarly unavailable if users are partitioned from the anointed
primary copies.

#### HATs for Everyone

[In recent research at UC Berkeley](http://arxiv.org/pdf/1302.0309.pdf),
we show that high availability and transactions are *not* mutually
exclusive: it is possible to match the semantics provided by many of
today's "ACID" and "NewSQL" databases without sacrificing high
availability. While these Highly Available Transactions (HATs) do not
provide serializability---which is not highly available under
arbitrary read/write transactions---[as I blogged about last
week]({{site.baseurl}}/when-is-acid-acid-rarely/), many ACID databases
provide a weaker form of isolation. The problem is that these
databases do not *implement* their guarantees using highly available
algorithms. However, as our recent results demonstrate, we *can*
implement these guarantees and achieve other useful properties without
giving up high availability or having to incur cross-replica (or, in a
georeplicated scenario, cross-datacenter) latencies.

At a high level, HATs provide several guarantees that can be achieved
with high availability<sup><a class="no-decorate"
href="#availability-note">2</a></sup> for arbitrary read/write
transactions across a given set of data items, irrespective of data
layout:

1. Transactional atomicity across arbitrary data items (e.g., see all
or none of a transaction's updates, or "A" in "ACID"), regardless of
how many shards a transaction accesses and without using a master.

2. ANSI-compliant Read Committed and Repeatable Read isolation levels<sup><a class="no-decorate"
href="#ansi-note">3</a></sup>
("I" in "ACID" matching many existing databases).

3. Session guarantees including read-your-writes, monotonic reads
(i.e., time doesn't go backwards), and causality within and across
transactions.

4. Eventual consistency, meaning that, if writes to a data item stop,
all transaction reads will eventually return the last written value.

We believe that this is the strongest set of guarantees that have been
provided with high availability, and many of the algorithms---like the
atomicity and isolation guarantees---are brand new, namely because
they don't use masters or other coordination on transactions' fast
paths. [The brief report we just released](http://arxiv.org/abs/1302.0309)
runs slightly over five pages and includes sample algorithms for each
guarantee.

#### Trade-offs

Of course, there are several guarantees that HATs cannot provide. Not
even the best of marketing teams can produce a real database that
"beats CAP"; HATs cannot make guarantees on data recency during
partitions, although, in the absence of partitions, data [may not be
very stale](http://pbs.cs.berkeley.edu/#demo). HATs cannot be "100%
ACID compliant" as they cannot guarantee serializability, yet they
meet the default and sometimes maximum guarantees of many "ACID"
databases. HATs cannot guarantee global integrity constraints
(e.g., uniqueness constraints across data items) but can perform local
checking of predicates (e.g., per-record integrity maintenance like
null value checks). In the report, we classify many of these anomalies
in terms of previously documented isolation levels.

Are these guarantees worthwhile? If users need high availability or
low latency, HATs provide a set of semantics that is stronger than any
existing highly available data store. If users need strong consistency
guarantees, they will need to accept the possibility of unavailability
and expect to pay at least one round trip time for each of their
operations. As an example, people often ask me about [Spanner, from
Google](http://www.wired.com/wiredenterprise/2012/11/google-spanner-time/). Spanner
provides strong consistency and typically low latency read-only
transactions. Users that are partitioned from the majority of Spanner
nodes will experience unavailability and read-write transactions will
incur WAN latencies due to Spanner's two-phase locking
mechanism. Spanner's authors don't hide these facts---for example,
[look at Table 6 on page 12 of the
paper](http://static.googleusercontent.com/external_content/untrusted_dlcp/research.google.com/en/us/archive/spanner-osdi2012.pdf):
read/write transactions are between 8.3 and 11.9 times slower than
read-only transactions. For Google, who has optimized their WAN
networks, atomic clocks, and infrastructure engineering and whose
workload (also in Table 6) is composed of over 98% of read-only
transactions, Spanner makes sense. When high availability and
guaranteed low latency matter, even Google might choose a different
architecture.

#### Coming soon

Our work on HATs at Berkeley is just beginning. We're benchmarking a
HAT prototype and are tuning our algorithms for performance and
scalability. Once the algorithms are better explored, I would
personally like to help integrate HATs into existing data stores, much
as we recently did with our [PBS work in
Cassandra]({{site.baseurl}}/using-pbs-in-cassandra-1.2.0/). It'd be
interesting to port an application running on Oracle Database to a
NoSQL store and provide the same semantic guarantees with
substantially improved performance, availability, and cost
effectiveness. We're also working on additional theoretical results to
further explain HATs in the context of CAP. I plan to share these
results as we develop them further.

In the meantime, we'd welcome feedback on our work so far and are
curious where HATs make sense in your stack. If you're an application
developer who wishes she had transactional atomicity or weak
isolation, a distributed database developer interested in HATs, or you
just think HATs are cool, let us know. We're always looking for
anecdotes, workloads, and conversation.

**This is Part Two of a two part series on Transactions and
Availability.<br> [Part One: When is ACID
ACID?]({{site.baseurl}}/when-is-acid-acid-rarely/)**

*This research is joint work with [Alan
 Fekete](http://www.cs.usyd.edu.au/~fekete), [Ali
 Ghodsi](http://www.cs.berkeley.edu/~alig/), [Joe
 Hellerstein](http://db.cs.berkeley.edu/jmh/), and [Ion
 Stoica](http://www.cs.berkeley.edu/~istoica/).*

<hr>
<span id="footnotetitle">Footnotes</span>

<p><span class="footnote" id="cap-note" markdown="1"><a
class="no-decorate" href="#cap-note">\[1\]</a>&nbsp;[As formally
proven by Gilbert and
Lynch](http://lpd.epfl.ch/sgilbert/pubs/BrewersConjecture-SigAct.pdf),
the CAP Theorem states that
[linearizability](http://en.wikipedia.org/wiki/Linearizability) and
high availability are incompatible. Linearizability is often called
"atomicity," yet "atomicity" means something different in database
parlance, namely, we see all or none of a transaction's updates. For
clarity, I'll call "ACID atomicity" "transactional atomicity."</span></p>

<p><span class="footnote" id="availability-note" markdown="2"><a
class="no-decorate" href="#availability-note">\[2\]</a>&nbsp;As we
discuss in Section 2 of the paper, we have to be careful how to define
"high availability": a system that always aborts all transactions is,
in a sense, "available," if not very useful. In short, we say that a
system provides high availability if every transaction that can
contact at least one server for each data item in the transaction
eventually commits (or alternatively, aborts itself due to an internal
integrity constraint violation). The system is not allowed to
indefinitely abort transactions for the purposes of maintaining
availability.</span></p>

<p><span class="footnote" id="ansi-note" markdown="3"><a
class="no-decorate" href="#ansi-note">\[3\]</a>&nbsp;If you're a
database nut, you may object that the ANSI SQL definitions are
[notoriously
underspecified](http://ftp.research.microsoft.com/pub/tr/tr-95-51.pdf). However,
rest assured that HAT "Read Committed" matches all of the definitions
we've found in the literature, including those by [Berenson et
al. (SIGMOD
1995)](http://ftp.research.microsoft.com/pub/tr/tr-95-51.pdf) and
[Adya (MIT Ph.D. thesis, ICDE
2000)](http://www.pmg.lcs.mit.edu/~adya/pubs/phd.pdf). HAT "Repeatable
Read"---and "Repeatable Read" interpretations in general---is more
complicated; HAT "Repeatable Read" does match the ANSI spec, and we
provide a detailed discussion in Section 4 of the paper.</span></p>