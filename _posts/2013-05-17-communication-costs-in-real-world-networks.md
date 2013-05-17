---
layout: post
title: "Communication Costs in Real-World Networks"
date: 2013-05-17
comments: false
---

*tl;dr: Network latencies in the wild can be expensive, especially at
 the tail and across datacenters: how bad are they, and what can we do
 about them? Make sure to explore the <a href="#explore">the demo</a>.*

Network latency makes distributed programming hard. Even when a
distributed system is fault-free, any communication between servers
affects performance. While the theoretical lower-bound on
communication delay is the speed of light---not horrible, at least
within a single datacenter---latencies are rarely this fast. I've been
working on and benchmarking [communication-avoiding
databases](http://www.bailis.org/blog/hat-not-cap-introducing-highly-available-transactions/)
and, as part of my research, I wanted to quantify the behavior of
real-world networks both within and across datacenters. This post
contains both an interactive <a href="#explore">demo</a> of what we
found, some high-level <a href="#highlevel_takeaways">trends</a>, and
some <a
href="#implications_for_distributed_systems_designers">implications</a>
for distributed systems designs.

I wasn't aware of any datasets describing network behavior both within
and across datacenters, so we launched m1.small Amazon EC2 instances
in each of the eight geo-distributed "Regions," across the three
us-east "Availability Zones" (three co-located datacenters in
Virginia), and within one datacenter (us-east-b). We measured RTTs
between hosts for a week, measuring ping times at a granularity of one
second.<sup><a class="no-decorate"
href="#methodology-note">1</a></sup>

<div id="explore" style="margin-top:1em;"><i>I've made the raw data <a
href="https://github.com/pbailis/aws-ping-traces">available on
Github</a> but, as an excuse to play with <a
href="http://d3js.org/">D3.js</a>, I built this interactive
visualization; select different percentiles and drag and zoom into the
graph:</i><sup><a class="no-decorate" href="#nc-note">2</a>,<a
class="no-decorate" href="#render-note">3</a></sup>

<iframe style="width:800px; height:800px; frame:0px;" frameborder="0" src="http://bailis.org/blog/post_data/2013-05-17/latencies.html">I suggest you enable iframes.</iframe>
</div>

#### High-level Takeaways

Aside from the absolute numbers and the raw data, I think that there
     are a few interesting trends. If you're a networking guru, these
     may be obvious, but I found the magnitude of these trends
     surprising. *(N.B. These aren't necessarily Amazon-specific, and
     this is hardly an indictment of AWS.)*<sup><a class="no-decorate"
     href="#latency-lit-note">4</a></sup>

 * **Latency >> Speed of Light** The minimum RTT between any two nodes
     was 227µs---almost two orders of magnitude higher than the
     theoretical minimum. Across continents, latencies were also
     higher: Dublin to Sydney could take around 58 milliseconds but
     requires around 350ms on average. Instead, routers, network
     topologies, virtualization, and the end-host software stack all
     get in the way.

 * **Average << Tail** Within us-east-b, ping times averaged around
     400µs; this is close to Jeff Dean's figure from his [Numbers
     Everyone Should
     Know](http://www.eecs.berkeley.edu/~rcs/research/interactive_latency.html). However,
     at the tail, latencies get much worse: at the 99.9th percentile,
     latency (again, within a single datacenter) rose to between 11.6
     and 21ms. At the 99.999th percentile, latency increased to
     between 84 and 151ms---a 160 to 350x increase over the average!

 * **Cross-Datacenter Communication is Expensive** On average,
     communicating across availability zones was 2--7x slower than
     communicating within an availability zone; communicating across
     geographic regions was 44--720x slower. There are several simple
     possibilities to account for the difference between
     regions---geographic distance being a major contributor. Notably,
     latencies for cross-geographic regions performed relatively
     better at the tail: at the 99.999th percentile, cross-region RTTs
     were only 1.4--45x slower than us-east RTTs. I suspect this is
     because transit delays on the wire are fixed, while routing and
     software-related delays are more likely to vary. However, the
     network distance between AZs *also* varied: us-east-b and
     us-east-c had a minimum RTT of 693µs but us-east-c to us-east-d
     had a minimum RTT of 1.31ms (and, on average, a difference of
     almost 3.5x); not all local DC communication links are equal.

#### Implications for Distributed Systems Designers

Aside from any particular statistical behavior or correlations, this
data highlights the importance of reasoning about latency in
distributed system design. While many [five-star
wizards](http://www.eecs.harvard.edu/~waldo/Readings/waldo-94.pdf) of
distributed computing [have long warned
us](https://blogs.oracle.com/jag/resource/Fallacies.html) of the
pitfalls of network latency, there are at least two additional
challenges today: almost every new system is distributed and many
systems are operating at larger scale than ever before. The former
means that more distributed systems developers need
[communication-avoiding
techniques](http://cs-www.cs.yale.edu/homes/dna/papers/abadi-pacelc.pdf),
while the latter means that [the tail will continue to
grow](http://dl.acm.org/citation.cfm?id=2408794). Even if we solve the
LAN latency problem, the lower bound on communication cost is still
much higher than that of local data access, and multi-datacenter
system deployments are increasingly common. While we can reduce some
inefficiencies today, there are fundamental barriers to improvement,
like the speed of light; I believe the solution to avoiding latency
penalties will come from better software, algorithms, and programming
techniques instead of better network hardware. [Better
languages](http://www.bloom-lang.net/),
[semantics](http://www.bailis.org/blog/hat-not-cap-introducing-highly-available-transactions/),
and
[libraries](http://hal.upmc.fr/docs/00/55/55/88/PDF/techreport.pdf)
are a start.

<hr>

<div id="footnotetitle">Footnotes</div>

<p><span class="footnote" id="methodology-note" markdown="1"><a
class="no-decorate" href="#methodology-note">\[1\]</a>&nbsp;There's a
non-negligible chance that this post generates debate with respect to
our methodology and the applicability of these results. Up front, I
think there's substantial room for improvement; my primary purpose for
this experiment was to demonstrate the considerable gap between LAN
and WAN latencies (if this is your cup of tea, let's talk!). It's
possible that EC2 virtualization and the choice of m1.small instances
could lead to higher latencies due to factors like multi-tenancy and
VM migration. There's also no doubt that larger packet sizes would
change these trends; indeed, in recent database benchmarking, we've
observed several additional effects related to local processing and
EC2 NIC behavior under heavy traffic. Please feel free to leave a
comment or get in contact, especially if you have suggestions for
improvement or have any data to share; I'll gladly link to it and use
it if possible.</span></p>

<p><span class="footnote" id="nc-note" markdown="2"><a
class="no-decorate" href="#nc-note">\[2\]</a>&nbsp;If you like this
stuff, there's some really cool research that studies the
metric spaces that arise from network topologies; one of my favorite
papers is ["Network Coordinates in the
Wild"](http://www.eecs.harvard.edu/~syrah/nc/wild07.pdf) by Ledlie et
al. in NSDI 2007, which applies network coordinates to the (real-world/"production") Azureus
file sharing network.</span></p>

<p><span class="footnote" id="render-note" markdown="3"><a
class="no-decorate" href="#render-note">\[3\]</a>&nbsp;My apologies
for overlaying the cross-AZ and the us-east results on top of the
cross-region data. I looked into pinning each of these two clusters in
designated locations but was only able to pin one at a time and
eventually gave up, settling for the effect that auto-adjusts the label
size.</span></p>

<p><span class="footnote" id="latency-lit-note" markdown="4"><a
class="no-decorate" href="#latency-lit-note">\[4\]</a>&nbsp;I don't
study networks (rather, I spend my time building systems on top of
them), but there's a lot of ongoing work on alleviating these
problems. For a short position paper regarding what *should* be
possible and what we may need to fix, check out ["It's Time For Low
Latency"](http://www.scs.stanford.edu/~rumble/papers/latency_hotos11.pdf)
by Rumble et al. in HotOS 2011.</span></p>

