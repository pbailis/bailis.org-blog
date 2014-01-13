---
layout: post
title: "Stickiness and client-server session guarantees"
date: 2014-1-13
comments: false
---

#### Session Guarantees

One of the most common consistency requirements I encounter in modern
web services is a guarantee called "read your writes" (RYW): each
user's reads should reflect its prior writes. This guarantees that,
for example, once I successfully post a Tweet, I'll be able to read it
after a page refresh. Without RYW, I have no idea whether my update
succeeded or was lost, and I might end up posting *again*, resulting
in a second update.

RYW is part of a larger set of ["session
guarantees"](http://www.cs.utexas.edu/~lorenzo/corsi/cs380d/papers/SessionGuaranteesBayou.pdf)
developed in the 1990s (and [popularized by Werner Vogels](http://queue.acm.org/detail.cfm?id=1466448); [also useful](http://pages.cs.wisc.edu/~cs739-1/papers/consistencybaseball.pdf)). These session guarantees are useful for at least two
reasons. First, they capture intuitive requirements for end-user
behavior: RYW and other guarantees, like "monotonic reads" (roughly
requiring that time doesn't appear to go backwards) are easy to
understand and, as we saw above, often desirable for human-facing services. Second,
session guarantees are cheap: while stronger models like
[linearizability](http://en.wikipedia.org/wiki/Linearizability) ("C"
in [CAP](http://henryr.github.io/cap-faq/)) provide every session
guarantee and then some, they are notoriously expensive---usually
requiring unavailability during partial failure and [increased
latency](http://cs-www.cs.yale.edu/homes/dna/papers/abadi-pacelc.pdf). What
early systems like
[Bayou](http://zoo.cs.yale.edu/classes/cs422/2013/bib/terry95managing.pdf)
discovered is that there are implementation techniques for achieving
session guarantees without paying these costs.

#### Session Guarantees and Availability

Interestingly (and as the subject of this post), most---but not
all---session guarantees are achievable with CAP-style
availability. [Gilbert and Lynch's proof of the CAP
Theorem](http://lpd.epfl.ch/sgilbert/pubs/BrewersConjecture-SigAct.pdf)
defines availability by requiring that every non-failing server
guarantees a response to each request despite arbitrary network
partitions between the servers. So, if we want to build an available
system providing the monotonic reads session guarantee, we can ensure
that read operations only return writes when the writes are present on
all servers. This ensures that, regardless of which server a client
connects to, it won't be forced to read older data and "go back in time."

Via a classic partitioning argument, we can see what RYW is not
achievable under this stringent availability model. We can partition a
client C away from all but one server S and require C to perform a
write. If our implementation is available, S should eventually
acknowledge the write as successful. If C reads from S, it'll achieve
RYW. But, what if we partition C away from S and allow it to only
communicate with server T? If we require C to perform a read, T will
have to respond, and C will not read its prior write. This demonstrates
that it's not possible to guarantee RYW for arbitrary read/write
operations in an available manner.

In our recent work on [Highly Available
Transactions](http://www.bailis.org/papers/hat-vldb2014.pdf), we
performed a similar analysis for each of the session guarantees, and
found that all but RYW are achievable with availability (see Figure 2
and Table 3 on page 8; perhaps surprisingly, this also means that
causal consistency is not available in a client-server model). The
question is: if RYW isn't available, why does it still seem to be
cheaper than, say, linearizability?

#### Sticky Availability and Mechanisms

To understand why RYW is still "cheap" but not quite as cheap as other
session guarantees, we formalized a new model of availability. RYW is
indeed achievable (as Vogels points out), if clients stay connected,
or are "sticky" with, a server (really, a complete copy of the
database). This is a stronger assumption than CAP-style availability,
but it's still much weaker than, say, requiring that clients contact a
majority of servers. In the [HAT
paper](http://www.bailis.org/papers/hat-vldb2014.pdf), we formalize
this as "sticky availability" (page 4, Section 4.1).

In practice, there are two primary ways of achieving sticky
availability. First (and easier) is to rethink the definition of a
"server": if clients cache their writes (thereby acting as a "server"
in our above model), they'll be able to read them in the future. By
keeping a local copy of data, the clients trivially maintain
stickiness. Several systems (including systems from both [our
group](http://www.bailis.org/papers/bolton-sigmod2013.pdf) and [Marc
Shapiro's CRDT group](http://arxiv.org/pdf/1310.3107.pdf)) leverage
these techniques and can provide unparalleled low latency. The problem
here is that caches can grow large, and, based on my experiences, it's
unclear how well this works for general-purpose applications. Second,
clients can use sticky request routing to ensure their requests always
contact the same servers. In a single datacenter, this can be
difficult, requiring the storage tier's request routers to know the
identity of the end-user making a request. This is feasible but
potentially requires tight coupling between application logic and the
database. In a multi-datacenter deployment, if each datacenter has a
linearizable cluster (e.g.,
[COPS](http://www-users.cselabs.umn.edu/classes/Fall-2012/csci8980-2/papers/cops.pdf)),
users can be assigned to a given region and their requests routed at
the edge---also doable, but with availability penalties.

In my experience, sticky routing is more common, with memcached acting
as a non-durable cache with likely (but not guaranteed)
stickiness. However, I'm not aware of any public accounts of actual
sticky available (but non-linearizable) architectures, hinting that
these approaches may either fall into the realm of what Jim Gray calls
"exotics" or, more optimistically, may simply be on the engineering horizon.

#### Why Sticky Availability Deserves More Study

Stickiness only becomes evident in a client-server model. In
traditional models of distributed computing, stickiness is often
guaranteed by default. If we consider a set of communicating processes
(take [Lamport's paper on
causality](http://www.cs.utexas.edu/users/lorenzo/corsi/cs380d/papers/time-clocks.pdf)
or even the CAP proof), each process (modulo limits on memory
capacity) can trivially observe its past actions. This model
effectively *presumes* the existence of a cache in the form of process
memory. In a classic client-server model, the server is often tasked
with maintaining the client's state. This is, in most cases,
fundamental to the utility of the system architecture. Yet, as we have
seen above, remembering the past in the client-server
model---especially without stateful clients---is non-trivial! The
difference between these models is subtle but makes a big difference
in practice, and I don't think the implications have been sufficiently
explored.

I also find it interesting that most implementations of the available
session guarantees (even those in Bayou) presume sticky
availability. While every session guarantee except RYW is achievable
with availability, they're often implemented using sticky available
mechanisms! This means that these implementations are "less available"
than they could be, with implications for latency, fault tolerance,
and scalability. The trade-off is between what I'll call "per-user
visibility" and availability. In our above, available implementation
of monotonic reads, a write might never become visible to any readers
if a non-failed server is permanently partitioned. In contrast, if we
have stickiness, the write can become visible to the writer (and,
possible, other readers) without sacrificing liveness. I haven't seen
a system evaluate this trade-off in depth, though many systems
(including the HAT research) have addressed the more general (and
classic) trade-off between global visibility and scalability.

As a final note, sticky available guarantees still face many of the
same problems as traditional available systems when it comes to
[maintaining application
correctness](http://www.youtube.com/watch?v=_rAdJkAbGls). Mutual
exclusion is unavailable, so how does RYW help applications? The
per-user visibility benefits are useful to end-users, but this is
often a matter of user experience rather than an issue of data
integrity. One benefit is that web services are frequently
single-writer-per-data-item, meaning conflicts are rare or impossible
as long as the single writer observes her updates. But, in general, I
haven't encountered many constraints on *data* that benefit from stickiness.