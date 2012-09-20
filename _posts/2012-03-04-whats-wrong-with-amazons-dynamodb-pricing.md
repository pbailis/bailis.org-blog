---
layout: post
title: "What's wrong with Amazon's DynamoDB pricing?"
date: 2012-03-04
---

*tl;dr: There's no good reason why strong consistency should cost double what eventual consistency costs. Strong consistency in DynamoDB shouldn't cost Amazon anywhere near double and wouldn't cost you double if you ran your own data store. While the benefit to your application may not be worth this high price, hiding consistency statistics encourages you to overpay.*

Amazon recently released an open beta for [DynamoDB](http://aws.amazon.com/dynamodb/), a hosted, "fully managed NoSQL database service."  DynamoDB automatically handles database scaling, configuration, and replica maintenance under a pay-for-throughput model. Interestingly, DynamoDB costs [twice as much for consistent reads](http://aws.amazon.com/dynamodb/pricing/) compared to [eventually consistent](http://en.wikipedia.org/wiki/Eventual_consistency) reads. This means that if you want to be guaranteed to read the data you last wrote, you need to pay double what you could be paying otherwise.

Now, I can't come up with any good *technical* explanation for why consistent reads cost 2x (and this is what I'm [handsomely compensated](http://bailis.org/research.html) to do all day). As far as I can tell, this is purely a *business* decision that's **bad for users**:

 1. The cost of strong consistency to Amazon is low, if not zero. To you? 2x.
 2. If you were to run your own distributed database, you wouldn't incur this cost (although you'd have to factor in hardware and ops costs).
 3. Offering a "consistent write" option instead would save you money and latency.
 4. If Amazon provided SLAs so users knew how well eventual consistency worked, users could make more informed decisions about their app requirements and DynamoDB. However, Amazon probably wouldn't be able to charge so much for strong consistency. 

I'd love if someone (read: from Amazon) would tell me why I'm wrong.

The cost of consistency for Amazon is low, if not zero. To you? 2x.
------------------------------------------------------------------------

Regardless of the replication model Amazon chose, I don't think it's possible that it's costing them 2x to perform consistent reads compared to eventually consistent reads:

**Dynamo-style replication.** If Amazon decided to stick to their original [Dynamo](http://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf) architecture, then all reads and writes are sent to all replicas in the system. When you perform an eventually consistent read, it means that DynamoDB gives you an answer when the first replica (or first few replicas) reply. This cuts down on latency: after all, waiting for the first of three replicas to reply is faster than waiting for a single replica to respond! However, all of the replicas will eventually respond to your request, whether you wait for them or not.

This means that eventually consistent reads in DynamoDB would use the same number of messages, amount of bandwidth, and processing power as strongly consistent reads.  It shouldn't cost *Amazon* any more to perform consistent reads, but it costs *you* double.

If you ran your own Dynamo-style NoSQL database, like [Riak](http://basho.com/), [Cassandra](http://cassandra.apache.org/), or [Voldemort](http://project-voldemort.com/), you wouldn't have this artificial cost increase when choosing between eventual and strongly consistent reads.

*Possible explanations:* Maybe Amazon didn't adopt the Dynamo design's "send-to-all" semantics. This would save bandwidth but cause a  *significant* latency hit. However, Amazon might save in terms of messages and I/O without compromising latency if they chose not to send read requests to remote sites (e.g., across availability zones) for eventually consistent reads . Another possibility is that, because  eventual consistency is faster, transient effects like queuing are  reduced, which helps with their back-end provisioning. Regardless, none of these possibilities necessitate a 2x price increase. Note that the Dynamo model covers most variants of quorum replication plus anti-entropy. **edit: As I mentioned, it's possible that weak consistency saves an extra I/O per read. However, I'm still unconvinced that this leads to a 2x TCO increase.**

*Cost to Amazon: probably zero*

**Master-slave replication.** If Amazon has chosen a master-slave replication model in DynamoDB, eventually consistent reads could go to a slave, reducing load on the master. However, this would mean Amazon is performing some kind of *monetary-cost-based* load-balancing, which seems strange and hard to enforce. Even if this is the case, is doubling the price really the right setting for proper load-balancing at all times and for all data? Is the 2x cost bump really necessary? I'm not convinced.

If you ran your own NoSQL store that used master-slave replication, like [HBase](http://hbase.apache.org/) or [MongoDB](http://www.mongodb.org/), you wouldn't be faced with this 2x cost increase for strong consistency.

*Cost to Amazon: increased master load. 2x load? Probably not, given proper load balancing.*

Read vs. Write Cost
-------------------

Amazon decided to place this extra charge on the read path. Instead, they could have offered a "consistent write" option, where all subsequent reads would return the data you wrote. This would slow down consistent writes (and speed up reads). I'd wager that a vast majority of DynamoDB operations are reads, so this "consistent write" option would decrease revenue compared to the current "consistent read" option. So, compared to a consistent write option, you're currently getting charged more, and the majority of your DynamoDB operations are slower.

FUD Helps Sell Warranties
--------------------

Amazon is vague about eventual consistency in DynamoDB. Amazon [says that](http://aws.amazon.com/dynamodb/faqs/#What_is_the_consistency_model_of_Amazon_DynamoDB):

> Consistency across all copies of data is usually reached within a second. Repeating a\[n eventually consistent\] read after a short time should return the updated data.

What does "usually" mean? What's "a short time"? These are imprecise metrics, and they certaintly aren't guarantees. This may be intentional.

Best Buy tries to sell you an in-house extended warranty when you buy a new gadget. Most of the time, you don't buy the warranty because you make a judgment that the chance of failure isn't worth the price of the warranty. With DynamoDB, you have no idea what the likelihood of inconsistency is, except that "a second" is "usually" long enough. What if you don't want to wait?  What about the best case? Or the worst? Amazon *could* release a distribution for these delays so you could make an informed decision, but they don't. Why not?

It's not for technical reasons. Amazon has to know this distribution. I've spent the last six months thinking about [how to provide SLAs for consistency](http://bailis.org/projects/pbs/#demo). Our new [techniques](http://www.eecs.berkeley.edu/Pubs/TechRpts/2012/EECS-2012-4.pdf) show that you can make predictions with arbitrary precision simply by measuring message delays. Even without our work, I'd bet all my chips on the fact that Amazon has tested the hell out of their service and know exactly how *eventual* eventual consistency is in DynamoDB. After all, if the window of inconsistency was prohibitively long, it's unlikely that Amazon would offer eventual consistency as an option in the first place.

With more information, most customers probably wouldn't pay 2x
---------------------------------------------------------------

So why doesn't Amazon release this data to customers? There are several business reasons that disincentivize them from doing so, but the basic idea is that *it's not clear that strong consistency delivers a 2x value to the customer in most cases*. However, without the data, customers can't make this call for themselves without a lot of benchmarking. And profiling doesn't buy you any guarantees like an SLA.

-  If users knew what "usually" really meant, they could make intelligent decisions about pricing. How many people would pay double for strong consistency if they'd only have to wait a few tens of milliseconds on *average* for consistent read, or, conversely, that data would be at most a few tens of milliseconds stale? What if 99.9% of reads were fresh within 100ms? 200ms? 500ms? 1000ms? Without the distribution, it's hard to judge whether eventual consistency works for a given app.

- Related: if your probability of consistent reads is sufficiently high (say, 99.999%) after normal client-side round-trip times (which are often long), do you really care about strong consistency? If you did, you could also intentionally block your readers until they would read consistent data with a high enough probability.

- If you have "[stickiness](http://www.allthingsdistributed.com/2008/12/eventually_consistent.html)" and your requests are always sent to a given DynamoDB instance (which *you* can't enforce but is a likely design choice!), then you may *never* read inconsistent data, even under eventual consistency. Even if this happens only some of the time, you'll see less stale data. This is due to what are known as [session guarantees](http://www.cs.utexas.edu/~dahlin/Classes/GradOS/papers/SessionGuaranteesPDIS.pdf).

- It's not specified how much slower a consistent read is compared to an eventually consistent read, so it's possible that the wait time until (a high probability of) consistency plus the latency of an eventually consistent read is actually *lower* than the latency of a strongly consistent read.

- If you store timestamps with your data, you can guarantee you don't read old data (another session guarantee) and, if you're dissatisfied, you can repeat your eventually consistent read. You can calculate the expected cost of reading consistent data across multiple eventually consistent reads---if you have this data.

I don't think many people would pay 2x for their reads if they were provided with this data or some consistency SLA.  Maybe some total *rockstars* are okay with this vagueness, but it sure seems hard to design a reliable service without any consistency guarantees from your backend. By only giving users an extremely conservative upper bound on the *eventuality* of reads (say, if your clients switch between data centers between reads and writes *and* DynamoDB experiences extremely high message delays), Amazon may be scaring the average (prudent) user into paying more than they probably should. 

Conclusion
----------

Strong consistency in DynamoDB probably doesn't cost Amazon much (if anything) but it costs you twice as much as eventual consistency. It's highly likely that Amazon has quantitative metrics for eventual consistency in DynamoDB, but keeping those numbers private makes you more likely to pay extra for guaranteed consistency. Without those numbers, it's much harder for you to reason about your application's behavior under average-case eventual consistency.

Sometimes you absolutely need strong consistency. Pay in those cases. However, especially for web data, eventual is often good enough. The current problem with DynamoDB is that, because customers don't have access to quantitative metrics about their window of inconsistency, it's easy for Amazon to set prices irrationally high.

**Disclaimer: I (perhaps obviously) have no privileged knowledge of Amazon's AWS architecture (or any other parts of Amazon, for that matter). [I just happen to spend a lot of time thinking about and working on cool distributed systems problems](http://bailis.org/research.html).**
