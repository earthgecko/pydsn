A fork of the @russss and @odysseus654 library to parse the NASA Deep Space
Network feed used by http://eyes.nasa.gov/dsn.

Configurable to populate:

* twitter
* A MySQL database
* hipchat
* statsd/buckyserver -> Graphite with metrics for:
  * stations
  * dishes
  * spacecraft

Work in progress.

## dsn.conf

You need to add a dsn.conf file in the pydsn root directory, it should look like
dsn.conf.example

## Running

The pydsn services are currently run with supervisord, however can be run any
which way you choose.

While ironing out some issues, it is recommended that you use a simple bash
script and cron every minute to monitor the pydsn services logs and if the log
has not been written too in 40 seconds, restart the service.

## Using local data xml

Due to the dsn, dsn_dbsync and dsn_metrics all having the capability to fetch
the xml data from NASA, they all use the local copy if it is less than 10
seconds old.  This also means that all the services are reporting on the same
data at 10 second resolution.

## Skyline

This fork is really about trying to machine learn the spacecraft comms behaviour
with Skyline and try to bring some machine learning to Skyline.  After all
machine learning with timeseries is not easy.  The DSN comms data set adds a
large amount of classifiable aspects, which supplements the metrics timeseries
with classifiable classes and multi-seasonalities on each class, whether that is
a yearly seasonality on dish[windspeed] or which dish which spacecraft normally
connects to when.  What is the seasonality in the signal strengths relative to
oribtal positions of Earth and spacecraft?  Is there one?  Do the b/s get less
over time from Voyager 2 and Voyager 1 with increasing distance?  With plasma
tsunamis?

It is a goldmine data set, keep it away from Kaggle :)  Like Kepler but a bit
different :)

Can we detect anomalies in the DSN data either via Shewhart 3-sigma based
statistical process control and machine learning?

This is an attempt to find out.
