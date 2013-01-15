#!/bin/bash

echo 'Setting up cluster...'
git clone https://github.com/pcmanus/ccm.git
cd ccm && sudo ./setup.py install
ccm create pbstest -v 1.2.0

# set up aliases for Mac Users
# sudo ifconfig lo0 alias 127.0.0.2
# sudo ifconfig lo0 alias 127.0.0.3
# sudo ifconfig lo0 alias 127.0.0.4
# sudo ifconfig lo0 alias 127.0.0.5

ccm populate -n 5
ccm start
export CASS_HOST=127.0.0.1
echo '...cluster setup done'

echo 'Enabling PBS logging...'
wget http://downloads.sourceforge.net/cyclops-group/jmxterm-1.0-alpha-4-uber.jar
echo 'run -b org.apache.cassandra.service:type=PBSPredictor enableConsistencyPredictionLogging' | java -jar jmxterm-1.0-alpha-4-uber.jar -l $CASS_HOST:7100
echo 'PBS logging enabled...'

echo 'Running stress tests...'
cd ~/.ccm/repository/1.2.0/
chmod +x tools/bin/cassandra-stress
tools/bin/cassandra-stress -d $CASS_HOST -l 3 -n 10000 -o insert
tools/bin/cassandra-stress -d $CASS_HOST -l 3 -n 10000 -o read
echo '...stress tests done'

echo 'Running predictions...'
bin/nodetool -h $CASS_HOST -p 7100 predictconsistency 3 100 1
echo '...cool, right? Congratulations!'
