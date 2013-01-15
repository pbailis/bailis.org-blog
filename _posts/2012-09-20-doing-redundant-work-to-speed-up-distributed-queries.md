---
layout: post
title: "Doing redundant work to speed up distributed queries"
date: 2012-09-20
comments: false
---

*tl;dr: In distributed data stores, redundant operations can
 dramatically drop tail latency at the expense of increased system
 load; different Dynamo-style stores handle this trade-off
 differently, and there's room for improvement.*

At scale, tail latencies matter. When serving high volumes of traffic,
even a miniscule fraction of requests corresponds to a large number of
operations.  Latency <a
href="http://perspectives.mvdirona.com/2009/10/31/TheCostOfLatency.aspx">
has a huge impact on service quality</a>, and looking at the *average*
service latency alone is often insufficient. Instead, folks running
high-performance systems at places like Amazon and Google look to the
tail when measuring their performance.<sup><a class="no-decorate"
href="#tailnote">1</a></sup> High variance often hides in distribution
tails: in a <a
href="http://static.googleusercontent.com/external_content/untrusted_dlcp/research.google.com/en/us/people/jeff/Berkeley-Latency-Mar2012.pdf">talk
at Berkeley last spring</a>, Jeff Dean reported a 95 percentile
latency of 24ms and a 99.9th percentile latency of 994ms in Google's
BigTable service---a 42x difference!

In distributed systems, there's a subtle and somewhat underappreciated
strategy for reducing tail latencies: doing redundant work. If you
send the same request to multiple servers, (all else equal) you're
going to get an answer back faster than waiting for a single
server. Waiting for, say, one of three servers to reply is often
faster than waiting for one of one to reply. The basic cause is due to
variance in modern service components: requests take different amounts
of time in the network and on different servers at different times.<a
class="no-decorate" href="#poweroftwonote"><sup>2</sup></a> In Dean's
experiments, BigTable's 99.9th percentile latency dropped to 50ms when
he sent out a second, redundant request if the initial request hadn't
come back in 10ms---a 40x improvement. While there's a cost associated
with redundant work---increased service load---the load increase may
be modest. In the example I've mentioned, Dean recorded only a 5%
total increase in number of requests.<sup><a class="no-decorate"
href="#deannote">3</a></sup>

Learning about Google's systems is instructional, but we can also
observe the trade-off between tail latency and load in several
publicly-available distributed data stores patterned on Amazon's
influential Dynamo data store. In the <a
href="http://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf">original
paper</a>, Dynamo sends a client's read and write requests to all
replicas for a given key. For writes, the system needs to update all
replicas anyway. For reads, requests are idempotent, so the system
doesn't necessarily <em>need</em> to contact all replicas---should it?
Sending read requests to all replicas results in a linear increase in
load compared to sending to the minimum required number of
replicas.<sup><a href="#consistencynote">4</a></sup> For
read-dominated workloads (like many internet applications), this
optimization has a cost. When is it worthwhile?

Open-source Dynamo-style stores have different answers. Apache
Cassandra originally sent reads to all replicas, but
[CASSANDRA-930](https://issues.apache.org/jira/browse/CASSANDRA-930)
and
[CASSANDRA-982](https://issues.apache.org/jira/browse/CASSANDRA-982)
changed this: one commenter [argued
that](https://issues.apache.org/jira/browse/CASSANDRA-982?focusedCommentId=12973721&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-12973721)
"in IO overloaded situations" it was better to send read requests only
to the minimum number of replicas. By default, Cassandra now sends
reads to the minimum number of replicas 90% of the time and to all
replicas 10% of the time, primarily for consistency purposes.<sup><a
class="no-decorate" href="#cassandrainternalsnote">5</a></sup>
(Surprisingly, the relevant JIRA issues don't even mention the latency
impact.)  LinkedIn's Voldemort also uses a
[send-to-minimum](https://github.com/voldemort/voldemort/blob/master/src/java/voldemort/store/routed/PipelineRoutedStore.java#L186)
strategy (and has evidently done so [since it was
open-sourced](https://github.com/voldemort/voldemort/blob/fbd0f95d62ac2c5e97e5a4df5a732e9342d60da1/src/java/voldemort/store/routed/RoutedStore.java#L230)). In
contrast, Basho Riak chooses the "true" Dynamo-style <a
href="https://github.com/basho/riak_kv/blob/42eb6951b369e3fd9a42f7f54fb7618a40f1a9fb/src/riak_kv_get_fsm.erl#L153">send-to-all</a>
read policy.

Who's right? What do these choices mean for a real NoSQL deployment?
We can do a back-of-the-envelope analysis pretty easily. For [one of
our recent papers](http://www.bailis.org/papers/pbs-vldb2012.pdf) on
latency-consistency trade-offs in Dynamo style systems, we obtained
latency data from Yammer's Riak clusters. If we run some simple Monte
Carlo analysis (script available
[here](https://github.com/pbailis/bailis.org-blog/blob/master/post_data/2012-09-20/dynamo-montecarlo.py)),
we see that---perhaps unsurprisingly---redundant work can have a big
effect on latencies. For example, at the 99.9th percentile, sending a
single read request to two servers instead of one is 17x faster than
sending to one---maybe worth the 2x load increase. Sending reads to
three servers and waiting for one is 30x faster. Pretty good!

<center>
<table cellpadding="6">
<tr>
<td></td>
<td></td>
<td colspan="6" align="center">Requests sent</td>
</tr>
<tr>
<td rowspan="7" align="center" style="padding-right:10px;">Responses<br />waited for</td>
</tr>
<tr>
<td ></td>
<td align="right"><b>1</b></td>
<td align="right"><b>2</b></td>
<td align="right"><b>3</b></td>
<td align="right"><b>4</b></td>
<td align="right"><b>5</b></td>
</tr>
<tr>
<td align="right"><b>1</b></td>
<td align="right">170.0</td>
<td align="right">10.7</td>
<td align="right">5.6</td>
<td align="right">4.8</td>
<td align="right">4.5</td>
</tr>
<tr>
<td align="right"><b>2</b></td>
<td ></td>
<td align="right">200.6</td>
<td align="right">33.9</td>
<td align="right">6.5</td>
<td align="right">5.3</td>
</tr>
<tr>
<td align="right"><b>3</b></td>
<td ></td>
<td ></td>
<td align="right">218.2</td>
<td align="right">50.0</td>
<td align="right">7.5</td>
</tr>
<tr>
<td align="right"><b>4</b></td>
<td ></td>
<td ></td>
<td ></td>
<td align="right">231.1</td>
<td align="right">59.8</td>
</tr>
<tr>
<td align="right"><b>5</b></td>
<td ></td>
<td ></td>
<td ></td>
<td ></td>
<td align="right">242.2</td>
</tr>
</table>
<div style="margin-top: 5px;"><b>99.9th percentile read latencies (in ms) for the Yammer Dynamo-style latency model.</b></div>
</center>

The numbers above assume you send both requests at the same time, but
this need not be the case. For [example](https://github.com/pbailis/bailis.org-blog/blob/master/post_data/2012-09-20/dynamo-multirequest-montecarlo.py), sending a second request if
the first hasn't come back within 8ms results in a modest 4.2%
increase in requests sent and a 99.9th percentile read latency of
11.0ms. This is due to the long tail of the latency distributions we
see in Yammer's clusters---we only have to speed up a small fraction
of queries to improve the overall performance.

To preempt any dissatisfaction, I'll admit that this analysis is
simplistic. First, I'm not considering the increased load on each
server due to sending multiple requests. The increased load may in
turn increase latencies, which would decrease the benefits we see
here. This effect depends on the system and workload. Second, I'm
assuming that each request is identically, independently
distributed. This means that each server behaves the same (according
to the Yammer latency distribution we have). This models a system
equally loaded, equally powerful servers, but this too may be
different in practice.<sup><a class="no-decorate"
href="#cassandrasnitchnote">6</a></sup> Third, with a different
latency distribution, the numbers will change. Real-world benchmarking
is the best source of truth, but this analysis is a starting point,
and you can easily play with different distributions of your own
either with the provided script or in your browser using <a
href="http://pbs.cs.berkeley.edu/#demo">an older demo</a> I built.

Ultimately, the balance between redundant work and tail latency
depends on the application. However, in latency-sensitive environments
(particularly when there are serial dependencies between requests)
this redundant work has a massive impact. And we've only begun: we
don't need to send to <em>all</em> replicas to see benefits---even one
extra request can help---while delay and cancellation mechanisms like the ones
that Jeff Dean hints at can further reduce load penalties. There's a
large amount of hard work and research to be done designing,
implementing, and battle-testing these strategies, but I suspect that
these kinds of techniques will have a substantial impact on future
large-scale distributed data systems.

*Thanks to [Shivaram Venkataraman](https://github.com/shivaram/), [Ali
 Ghodsi](http://www.cs.berkeley.edu/~alig/), [Kay
 Ousterhout](http://www.eecs.berkeley.edu/~keo/), [Patrick
 Wendell](http://www.pwendell.com/), [Sean
 Cribbs](https://twitter.com/seancribbs), and [Andy
 Gross](https://twitter.com/argv0) for assistance and feedback that
 contributed to this post.*

<hr>

<div id="footnotetitle">Footnotes</div>

<div class="footnote" id="tailnote"><a class="no-decorate"
href="#tailnote">[1]</a> There are <a
href="http://highscalability.com/latency-everywhere-and-it-costs-you-sales-how-crush-it">many
studies</a> of the importance of latency for different services. For
example, an <a
href="http://www.scribd.com/doc/4970486/Make-Data-Useful-by-Greg-Linden-Amazoncom">often-cited
statistic</a> is that an additional 100ms of latency cost Amazon 1% of
sales. In the systems community, David Anderson attributes this
sensitivity to tail latencies to both the original Dynamo paper and
Werner Vogels's subsequent evangelizing (buried in the comments <a
href="https://plus.google.com/115237092509505721130/posts/cf4sbedNd2W">here</a>).</div>

<div class="footnote" id="poweroftwonote"><a class="no-decorate"
href="#poweroftwonote">[2]</a> There's a large body of <a
href="http://www.eecs.harvard.edu/~michaelm/postscripts/handbook2001.pdf">theoretical
research</a> on "the power of two choices" that's related to this
phenomenon: if you select the less loaded of two randomly chosen
servers instead of randomly picking one, you can exponentially improve
a cluster's load balance. Theoreticians might quibble with this
analogy: after all, here, we're usually still sending requests to both
of the servers, and the original power of two work focuses on only
sending requests to the lighter-loaded server. However, this research
is still interesting to consider as a precursor to many of the
techniques here and as the start of a more rigorous understanding of
these trade-offs.</div>

<div class="footnote" id="deannote"><a class="no-decorate"
href="#deannote">[3]</a> Dean also describes the effect of different
delay and cancellation mechanisms. Cancellation seems tricky to get
right depending on the application. Intercepting and cancelling a
lightweight read request is harder (i.e., needs to be faster) than,
say, canceling a slower, more complex query. <a
href="https://www.usenix.org/conference/hotcloud12/why-let-resources-idle-aggressive-cloning-jobs-dolly">Recent
work</a> from some of my colleagues at UC Berkeley demonstrates
alternative algorithms for limiting the overhead of redundant work in
general-purpose cluster computing frameworks like Hadoop.</div>

<div class="footnote" id="consistencynote"><a class="no-decorate"
href="#consistencynote">[4]</a> Determining the minimum number of
replicas to read from depends on the desired consistency of the
operation. This is a complicated subject and is related to (but too
involved for) the main discussion here. In short, if we denote the
number of replicas as <em>N</em>, the number of replicas to block for
during reads as <em>R</em> and equivalently for writes as <em>W</em>,
<em>R</em>+<em>W</em> > <em>N</em> means you'll read your writes (each
key acts as a <a href="http://stackoverflow.com/a/8872960">regular
register</a>), while anything less gives you weak guarantees. For more
info, check out <a href="http://pbs.cs.berkeley.edu/#demo">some
research we recently did</a> on these latency-consistency
trade-offs.</div>

<div class="footnote" id="cassandrainternalsnote"><a
class="no-decorate" href="#cassandrainternalsnote">[5]</a> For readers
into hardcore Cassandra internals: currently, Cassandra fetches the
data from one server and requests "digests," or value hashes, from the
remaining (<em>R-1</em>) servers. In the case that the digests don't
match, Cassandra will perform another round of requests for the actual
values. Now, if a mechanism called <a
href="http://wiki.apache.org/cassandra/ReadRepair"><em>read
repair</em></a> is enabled, then Cassandra will randomly (as a
configurable parameter) send digest requests to all replicas (as
opposed to just the <em>R-1</em>). In the original patch, the
<em>default</em> probability of sending to all <a
href="https://github.com/apache/cassandra/blob/e5477338458c3a0229d4fbe659231002ac154583/src/java/org/apache/cassandra/config/CFMetaData.java#L52">was
100%</a> (all the time); <a
href="https://github.com/apache/cassandra/blob/a500e2835748f19d0c11bc3dfcecc71c50d9cf7e/src/java/org/apache/cassandra/config/CFMetaData.java#L67">it
is now 10%</a> (due&#8212;somewhat cryptically&#8212;to <a
href="https://issues.apache.org/jira/browse/CASSANDRA-3169">CASSANDRA-3169</a>). (Sources:
original patch <a
href="https://github.com/apache/cassandra/commit/e5477338458c3a0229d4fbe659231002ac154583#L5L394">here</a>;
latest code <a
href="https://github.com/apache/cassandra/blob/b38ca2879cf1cbf5de17e1912772b6588eaa7de6/src/java/org/apache/cassandra/service/StorageProxy.java#L859">here</a>;
filtering of endpoints done <a
href="https://github.com/apache/cassandra/blob/3a2faf9424769cfee5fdad25f4513611820ca980/src/java/org/apache/cassandra/service/ReadCallback.java#L97">here</a>)
This digest-based scheme is a substantial deviation from the Dynamo
design and exposes a number of other interesting trade-offs that
probably deserve further examination.</div>

<div class="footnote" id="cassandrasnitchnote"><a class="no-decorate"
href="#cassandrainternalsnote">[6]</a> For example, Cassandra's
"endpoint snitches" keep track of which nodes are "closest" according
to several different, configurable dimensions, including <a
href="https://github.com/apache/cassandra/blob/a500e2835748f19d0c11bc3dfcecc71c50d9cf7e/src/java/org/apache/cassandra/locator/DynamicEndpointSnitch.java">historical
latencies</a>. Depending on the configuration, if a given node is slow
or overloaded, Cassandra may choose not to read from it. I haven't
seen a performance analysis of this strategy, but, at first glance, it
seems reasonable.</div>

