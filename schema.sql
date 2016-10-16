CREATE TABLE `configDish` (
  `ID` tinyint unsigned NOT NULL AUTO_INCREMENT,
  `configSiteID` tinyint unsigned NOT NULL,
  `name` varchar(20) NOT NULL,
  `friendlyName` tinytext NOT NULL,
  `type` varchar(10) NOT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `name` (`configSiteID`,`name`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8;

CREATE TABLE `configSite` (
  `ID` tinyint unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(15) NOT NULL,
  `friendlyName` tinytext NOT NULL,
  `longitude` double NOT NULL,
  `latitude` double NOT NULL,
  `timezoneOffset` bigint DEFAULT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `name` (`name`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8;

CREATE TABLE `configSpacecraft` (
  `ID` smallint unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(20) NOT NULL,
  `friendlyName` tinytext,
  `lastID` smallint unsigned DEFAULT NULL,
  `encoding` varchar(10) DEFAULT NULL,
  `flags` set('Testing') NOT NULL DEFAULT '',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `lastID` (`lastID`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8;

CREATE TABLE `configState` (
  `ID` tinyint unsigned NOT NULL AUTO_INCREMENT,
  `state` varchar(100) NOT NULL,
  `upDown` enum('up','down') NOT NULL,
  `signalType` varchar(20) NOT NULL,
  `decoder1` enum('idle','out of lock','wait for lock','in lock') DEFAULT NULL,
  `decoder2` enum('off','out of lock','wait for lock','in lock') DEFAULT NULL,
  `encoding` varchar(10) DEFAULT NULL,
  `task` varchar(10) DEFAULT NULL,
  `flags` set('carrier','encoding') NOT NULL DEFAULT '',
  `valueType` enum('','data','carrier+','carrier','idle+','task','idle','none') NOT NULL DEFAULT '',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `state` (`state`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8;

CREATE TABLE `dataDish` (
  `ID` smallint unsigned NOT NULL AUTO_INCREMENT,
  `eventID` mediumint unsigned NOT NULL,
  `configDishID` tinyint unsigned NOT NULL,
  `createdTime` bigint NOT NULL,
  `updatedTime` bigint NOT NULL,
  `flags` set('MSPA','Array','DDOR','Testing') NOT NULL DEFAULT '',
  `targetSpacecraft1` smallint unsigned DEFAULT NULL,
  `targetSpacecraft2` smallint unsigned DEFAULT NULL,
  `targetSpacecraft3` smallint unsigned DEFAULT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `time_id` (`eventID`,`configDishID`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `dataDishLastPos` (
  `configDishID` tinyint unsigned NOT NULL,
  `azimuthAngle` float NOT NULL,
  `elevationAngle` float NOT NULL,
  `windSpeed` float NOT NULL,
  PRIMARY KEY (`configDishID`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `dataDishPos` (
  `eventID` mediumint unsigned NOT NULL,
  `configDishID` tinyint unsigned NOT NULL,
  `azimuthAngle` float NOT NULL,
  `elevationAngle` float NOT NULL,
  `windSpeed` float NOT NULL,
  PRIMARY KEY (`eventID`,`configDishID`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `dataEvent` (
  `ID` mediumint unsigned NOT NULL AUTO_INCREMENT,
  `time` bigint NOT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `tm` (`time`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `dataSignal` (
# @modified 20160925 - Bug #1666: dsn DB - dataSignal ID SMALLINT
#  `ID` smallint unsigned NOT NULL AUTO_INCREMENT,
  `ID` mediumint unsigned NOT NULL AUTO_INCREMENT,
  `eventID` mediumint unsigned NOT NULL,
  `dataDishID` smallint unsigned NOT NULL,
  `configDishID` tinyint unsigned NOT NULL,
  `upDown` enum('up','down') NOT NULL,
  `stateID` tinyint unsigned NOT NULL,
  `configSpacecraftID` smallint unsigned NOT NULL,
  `flags` set('slave','master') NOT NULL DEFAULT '',
  PRIMARY KEY (`ID`),
  KEY `sel` (`dataDishID`,`upDown`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `dataSignalDet` (
  `eventID` mediumint unsigned NOT NULL,
# @modified 20160925 - Bug #1666: dsn DB - dataSignal ID SMALLINT
#  `dataSignalID` samllint unsigned NOT NULL,
  `dataSignalID` mediumint unsigned NOT NULL,
  `dataRate` double DEFAULT NULL,
  `frequency` double DEFAULT NULL,
  `power` double DEFAULT NULL,
  PRIMARY KEY (`dataSignalID`,`eventID`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `dataSignalLastDet` (
# @modified 20160925 - Bug #1666: dsn DB - dataSignal ID SMALLINT
#  `dataSignalID` samllint unsigned NOT NULL,
  `dataSignalID` mediumint unsigned NOT NULL,
  `dataRate` double DEFAULT NULL,
  `frequency` double DEFAULT NULL,
  `power` double DEFAULT NULL,
  PRIMARY KEY (`dataSignalID`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `dataTarget` (
  `ID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `eventID` mediumint unsigned NOT NULL,
  `configDishID` tinyint unsigned NOT NULL,
  `configSpacecraftID` smallint unsigned NOT NULL,
  `uplegRange` double NOT NULL,
  `downlegRange` double NOT NULL,
  `rtlt` double NOT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `time_dish_craft` (`eventID`,`configDishID`,`configSpacecraftID`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `extDish` (
  `ID` smallint unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(15) NOT NULL,
  `site` varchar(15) NOT NULL,
  `friendlyName` varchar(15) DEFAULT NULL,
  `descr` tinytext,
  `latitude` double DEFAULT NULL,
  `longitude` double DEFAULT NULL,
  `created` smallint unsigned DEFAULT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `dish` (`name`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8;

INSERT INTO `extDish` (`ID`, `name`, `site`, `friendlyName`, `descr`, `latitude`, `longitude`, `created`) VALUES(1, 'DSS13', 'gdscc', 'Venus', '34m reflector with BWG optics', 35.247168, -116.794426, 1962);
INSERT INTO `extDish` (`ID`, `name`, `site`, `friendlyName`, `descr`, `latitude`, `longitude`, `created`) VALUES(2, 'DSS14', 'gdscc', 'Mars', '70m reflector', 35.426003, -116.889927, 1966);
INSERT INTO `extDish` (`ID`, `name`, `site`, `friendlyName`, `descr`, `latitude`, `longitude`, `created`) VALUES(3, 'DSS15', 'gdscc', 'Uranus', '34m HEF reflector', 35.421905, -116.887506, NULL);
INSERT INTO `extDish` (`ID`, `name`, `site`, `friendlyName`, `descr`, `latitude`, `longitude`, `created`) VALUES(4, 'DSS24', 'gdscc', 'Apollo', '34m reflector with BWG optics', 35.3397222222222, -116.874222222222, NULL);
INSERT INTO `extDish` (`ID`, `name`, `site`, `friendlyName`, `descr`, `latitude`, `longitude`, `created`) VALUES(5, 'DSS25', 'gdscc', 'Apollo', '34m reflector with BWG optics', 35.3377777777778, -116.875277777778, NULL);
INSERT INTO `extDish` (`ID`, `name`, `site`, `friendlyName`, `descr`, `latitude`, `longitude`, `created`) VALUES(6, 'DSS26', 'gdscc', 'Apollo', '34m reflector with BWG optics', 35.3555555555556, -116.873055555556, NULL);
INSERT INTO `extDish` (`ID`, `name`, `site`, `friendlyName`, `descr`, `latitude`, `longitude`, `created`) VALUES(7, 'DSS27', 'gdscc', 'Gemini', '34m reflector with BWG optics on highspeed mount', 35.2380555555556, -116.776388888889, NULL);
INSERT INTO `extDish` (`ID`, `name`, `site`, `friendlyName`, `descr`, `latitude`, `longitude`, `created`) VALUES(8, 'DSS28', 'gdscc', 'Gemini', '34m reflector with BWG optics on highspeed mount', 35.2380555555555, 116.778611111111, NULL);
INSERT INTO `extDish` (`ID`, `name`, `site`, `friendlyName`, `descr`, `latitude`, `longitude`, `created`) VALUES(13, 'DSS45', 'cdscc', NULL, '34m', -35.3983333333333, 148.977777777778, 1986);
INSERT INTO `extDish` (`ID`, `name`, `site`, `friendlyName`, `descr`, `latitude`, `longitude`, `created`) VALUES(11, 'DSS35', 'cdscc', NULL, '34m', -35.3951, 148.978599, 2014);
INSERT INTO `extDish` (`ID`, `name`, `site`, `friendlyName`, `descr`, `latitude`, `longitude`, `created`) VALUES(12, 'DSS43', 'cdscc', NULL, '70m', -35.4022222222222, 148.981111111111, 1973);
INSERT INTO `extDish` (`ID`, `name`, `site`, `friendlyName`, `descr`, `latitude`, `longitude`, `created`) VALUES(10, 'DSS34', 'cdscc', NULL, '34m BWG', -35.3983333333333, 148.981944444444, 1997);
INSERT INTO `extDish` (`ID`, `name`, `site`, `friendlyName`, `descr`, `latitude`, `longitude`, `created`) VALUES(14, 'DSS49', 'cdscc', NULL, '64m Parkes radio telescope (receive only)', -32.99835, 148.263554, 1961);
INSERT INTO `extDish` (`ID`, `name`, `site`, `friendlyName`, `descr`, `latitude`, `longitude`, `created`) VALUES(15, 'DSS54', 'mdscc', NULL, '34m BWG', 40.4255555555556, -4.25388888888889, NULL);
INSERT INTO `extDish` (`ID`, `name`, `site`, `friendlyName`, `descr`, `latitude`, `longitude`, `created`) VALUES(16, 'DSS55', 'mdscc', NULL, '34m BWG', 40.4241666666666, -4.2525, NULL);
INSERT INTO `extDish` (`ID`, `name`, `site`, `friendlyName`, `descr`, `latitude`, `longitude`, `created`) VALUES(17, 'DSS63', 'mdscc', NULL, '70m xmit: 400kW X+S, recv: L+S+X', 40.4311111111111, -4.24777777777778, 1974);
INSERT INTO `extDish` (`ID`, `name`, `site`, `friendlyName`, `descr`, `latitude`, `longitude`, `created`) VALUES(18, 'DSS65', 'mdscc', NULL, '34m HEF xmit: 20kW X, recv: S+X', 40.4269444444444, -4.25055555555556, 1987);

CREATE TABLE `extSpacecraft` (
  `ID` smallint unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(20) NOT NULL,
  `status` enum('','active','retired','silent','dead') NOT NULL,
  `launch` date DEFAULT NULL,
  `constellation` varchar(20) DEFAULT NULL,
  `friendlyName` tinytext,
  `location` varchar(100) DEFAULT NULL,
  `url` varchar(200) DEFAULT NULL,
  `agency` set('','nasa','esa','isro','apl','jpl','asi','isro','sao','noaa','isas','stsci','jaxa','lasp','arc') NOT NULL DEFAULT '',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `name` (`name`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8;

INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(2, 'intg', 'active', '2002-10-17', NULL, 'INTEGRAL - INTErnational Gamma-Ray Astrophysics Laboratory', 'Earth', 'http://sci.esa.int/integral/', 'esa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(3, 'mom', 'active', '2013-11-05', NULL, 'Mars Orbiter Mission', 'Mars', 'http://www.isro.gov.in/pslv-c25-mars-orbiter-mission', 'isro');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(4, 'msgr', 'dead', '2004-08-03', NULL, 'MESSENGER - MErcury Surface, Space ENvironment, GEochemistry, and Ranging', 'Mercury', 'https://www.nasa.gov/mission_pages/messenger/main/index.html', 'nasa,apl');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(5, 'go11', 'retired', '2000-05-03', 'GOES', 'GOES 11', 'Earth', 'http://www.goes.noaa.gov/', 'nasa,noaa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(6, 'go10', 'retired', '1997-04-25', 'GOES', 'GOES 10', 'Earth', 'http://www.goes.noaa.gov/', 'nasa,noaa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(7, 'go13', 'active', '2006-05-24', 'GOES', 'GOES 13', 'Earth', 'http://www.goes.noaa.gov/', 'nasa,noaa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(8, 'go12', 'active', '2001-07-23', 'GOES', 'GOES 12', 'Earth', 'http://www.goes.noaa.gov/', 'nasa,noaa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(9, 'go15', 'active', '2010-03-04', 'GOES', 'GOES 15', 'Earth', 'http://www.goes.noaa.gov/', 'nasa,noaa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(10, 'go14', 'active', '2009-06-27', 'GOES', 'GOES 14', 'Earth', 'http://www.goes.noaa.gov/', 'nasa,noaa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(11, 'grla', 'dead', '2011-09-10', 'GRAIL', 'GRAIL A - Gravity Recovery and Interior Laboratory', 'Moon', 'http://moon.mit.edu/', 'nasa,jpl');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(12, 'mms3', 'active', '2015-03-15', 'MMS', 'MMS 3 - Magnetospheric Multiscale', 'Earth', 'http://mms.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(13, 'mms2', 'active', '2015-03-15', 'MMS', 'MMS 2 - Magnetospheric Multiscale', 'Earth', 'http://mms.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(14, 'mms1', 'active', '2015-03-15', 'MMS', 'MMS 1 - Magnetospheric Multiscale', 'Earth', 'http://mms.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(15, 'stb', 'active', '2006-10-26', 'STEREO', 'STEREO B', 'Heliocentric', 'http://stereo.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(16, 'm01o', 'retired', '2001-04-07', NULL, 'Mars Odyssey', 'Mars', 'http://mars.nasa.gov/odyssey/', 'nasa,jpl');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(17, 'clu2', 'active', '2000-07-16', 'Cluster II', 'Cluster 2', 'Earth', 'http://sci.esa.int/cluster/', 'nasa,esa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(18, 'clu3', 'active', '2000-07-16', 'Cluster II', 'Cluster 3', 'Earth', 'http://sci.esa.int/cluster/', 'nasa,esa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(19, 'dawn', 'active', '2007-09-27', NULL, 'Dawn', 'Asteroid belt', 'http://discovery.nasa.gov/dawn.cfml', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(20, 'clu1', 'active', '2000-07-16', 'Cluster II', 'Cluster 1', 'Earth', 'http://sci.esa.int/cluster/', 'nasa,esa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(21, 'jno', 'active', '2011-08-05', NULL, 'Juno', 'Jupiter', 'http://www.missionjuno.swri.edu/', 'nasa,jpl');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(22, 'clu4', 'active', '2000-07-16', 'Cluster II', 'Cluster 4', 'Earth', 'http://sci.esa.int/cluster/', 'nasa,esa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(23, 'polr', 'retired', '1996-02-24', NULL, 'POLAR', 'Earth', 'http://pwg.gsfc.nasa.gov/polar/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(24, 'tdr5', 'active', '1991-08-02', 'TDRS', 'TDRS 5 - Tracking and Data Relay Satellite', 'Earth', 'http://tdrs.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(25, 'm01s', 'retired', '2001-04-07', NULL, 'Mars Odyssey', 'Mars', 'http://mars.nasa.gov/odyssey/', 'nasa,jpl');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(26, 'nhpc', 'active', '2006-01-19', NULL, 'New Horizons', 'Pluto', 'http://pluto.jhuapl.edu/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(28, 'mros', 'active', '2005-08-12', NULL, 'Mars Reconnaissance Orbiter', 'Mars', 'http://mars.nasa.gov/mro/', 'nasa,jpl');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(29, 'rose', 'active', '2004-03-02', NULL, 'Rosetta', 'Comet', 'http://rosetta.esa.int/', 'esa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(30, 'vex', 'silent', '2005-11-09', NULL, 'Venus Express', 'Venus', 'http://www.esa.int/Our_Activities/Space_Science/Venus_Express', 'esa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(31, 'gtl', 'active', '1992-07-24', NULL, 'GEOTAIL', 'Earth', 'http://pwg.gsfc.nasa.gov/geotail.shtml', 'nasa,isas');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(32, 'ice', 'silent', '1978-08-12', NULL, 'ISEE-3 Reboot', 'Heliocentric', 'http://spacecollege.org/isee3/', 'nasa,esa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(33, 'tdr8', 'active', '2000-06-30', 'TDRS', 'TDRS 8 - Tracking and Data Relay Satellite', 'Earth', 'http://tdrs.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(34, 'msl', 'active', '2011-11-26', NULL, 'Mars Science Laboratory (Curiosity)', 'Mars', 'http://mars.nasa.gov/msl/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(36, 'thc', 'active', '2007-02-17', 'THEMIS', 'THEMIS C / ARTEMAS P2', 'Moon - L2', 'http://cse.ssl.berkeley.edu/artemis/mission-overview.html', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(37, 'tdr3', 'active', '1988-09-29', 'TDRS', 'TDRS 3 - Tracking and Data Relay Satellite', 'Earth', 'http://tdrs.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(38, 'tdr1', 'retired', '1983-04-04', 'TDRS', 'TDRS 1 - Tracking and Data Relay Satellite', 'Earth', 'http://tdrs.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(39, 'tdr6', 'active', '1993-01-13', 'TDRS', 'TDRS 6 - Tracking and Data Relay Satellite', 'Earth', 'http://tdrs.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(40, 'mer2', 'silent', '2003-06-10', 'MER', 'Spirit', 'Mars', 'http://mars.nasa.gov/mer/home/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(41, 'tdr4', 'retired', '1989-03-14', 'TDRS', 'TDRS 4 - Tracking and Data Relay Satellite', 'Earth', 'http://tdrs.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(42, 'soho', 'active', '1995-12-02', NULL, 'SOHO - Solar and Heliospheric Observatory', 'Earth - L1', 'http://www.nasa.gov/mission_pages/soho/index.html', 'nasa,esa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(43, 'lade', 'dead', '2013-09-07', NULL, 'LADEE - Lunar Atmosphere and Dust Environment Explorer', 'Moon', 'http://www.nasa.gov/mission_pages/ladee', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(44, 'map', 'retired', '2001-06-30', NULL, 'WMAP - Wilkinson Microwave Anisotropy Probe', 'Heliocentric', 'http://map.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(45, 'vgr1', 'retired', '1977-09-05', 'Voyager', 'Voyager 1', 'Interstellar', 'http://voyager.jpl.nasa.gov/', 'nasa,jpl');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(46, 'chdr', 'active', '1999-07-23', NULL, 'Chandra X-ray Observatory', 'Earth', 'http://chandra.si.edu/', 'nasa,sao');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(47, 'no16', 'retired', '2000-09-21', 'NOAA', 'NOAA 16', 'Earth', 'http://www.goes.noaa.gov/', 'noaa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(48, 'vgr2', 'retired', '1977-07-20', 'Voyager', 'Voyager 2', 'Interstellar', 'http://voyager.jpl.nasa.gov/', 'nasa,jpl');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(49, 'musc', 'dead', '2003-05-09', NULL, 'Hayabusa', 'Asteroid belt', 'http://global.jaxa.jp/projects/sat/muses_c/', 'jaxa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(50, 'mer1', 'active', '2003-07-07', 'MER', 'Opportunity', 'Mars', 'http://mars.nasa.gov/mer/home/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(51, 'imag', 'silent', '2000-03-25', NULL, 'IMAGE', 'Earth', 'http://image.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(52, 'lro', 'retired', '2009-06-18', NULL, 'Lunar Reconnaissance Orbiter', 'Moon', 'http://lunar.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(53, 'grlb', 'dead', '2011-09-10', 'GRAIL', 'GRAIL B - Gravity Recovery and Interior Laboratory', 'Moon', 'http://moon.mit.edu/', 'nasa,jpl');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(54, 'mgs', 'silent', '1996-11-07', NULL, 'Mars Global Surveyor', 'Mars', 'http://mars.nasa.gov/mgs/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(55, 'dsco', 'active', '2015-02-11', NULL, 'DSCOVR - Deep Space Climate Observatory', 'Earth - L1', 'http://www.nesdis.noaa.gov/DSCOVR/', 'nasa,noaa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(56, 'phx', 'silent', '2007-08-04', NULL, 'Phoenix', 'Mars', 'http://phoenix.lpl.arizona.edu/', 'nasa,jpl');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(57, 'plc', 'active', '2010-05-20', NULL, 'Akatsuki', 'Venus', 'http://global.jaxa.jp/projects/sat/planet_c/', 'jaxa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(58, 'hyb2', 'active', '2014-12-03', NULL, 'Hayabusa 2', 'Asteroid belt', 'http://global.jaxa.jp/projects/sat/hayabusa2/', 'jaxa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(59, 'hst', 'active', '1990-04-24', NULL, 'Hubble Space Telescope', 'Earth', 'http://www.spacetelescope.org/', 'nasa,esa,stsci');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(60, 'ulys', 'retired', '1990-10-06', NULL, 'Ulysses', 'Heliocentric', 'http://solarsystem.nasa.gov/missions/profile.cfm?MCode=Ulysses', 'nasa,esa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(61, 'wind', 'active', '1994-11-01', NULL, 'WIND', 'Earth - L1', 'http://wind.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(62, 'tdr9', 'active', '2002-03-08', 'TDRS', 'TDRS 9 - Tracking and Data Relay Satellite', 'Earth', 'http://tdrs.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(63, 'thb', 'active', '2007-02-17', 'THEMIS', 'THEMIS B / ARTEMIS P1', 'Moon - L2', 'http://cse.ssl.berkeley.edu/artemis/mission-overview.html', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(64, 'mex', 'active', '2003-06-02', NULL, 'Mars Express', 'Mars', 'http://sci.esa.int/mars-express/', 'esa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(65, 'sdu', 'retired', '1999-02-07', NULL, 'Stardust', 'Comet', 'http://stardust.jpl.nasa.gov/home/index.html', 'nasa,jpl');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(66, 'sta', 'active', '2006-10-26', 'STEREO', 'STEREO A', 'Heliocentric', 'http://stereo.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(67, 'stf', 'active', '2003-08-25', NULL, 'Spitzer Space Telescope', 'Heliocentric', 'http://www.spitzer.caltech.edu/', 'nasa,jpl');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(68, 'mms4', 'active', '2015-03-15', 'MMS', 'MMS 4 - Magnetospheric Multiscale', 'Earth', 'http://mms.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(69, 'no18', 'active', '2005-05-20', 'NOAA', 'NOAA 18', 'Earth', 'http://www.goes.noaa.gov/', 'noaa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(70, 'ace', 'active', '1997-08-25', NULL, 'ACE - Advanced Composition Explorer', 'Earth - L1', 'http://www.swpc.noaa.gov/products/ace-real-time-solar-wind', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(71, 'cas', 'active', '1997-10-15', NULL, 'Cassini', 'Saturn', 'http://saturn.jpl.nasa.gov/', 'nasa,esa,jpl,asi');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(72, 'no17', 'retired', '2002-06-24', 'NOAA', 'NOAA 17', 'Earth', 'http://www.goes.noaa.gov/', 'noaa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(73, 'dif', 'silent', '2005-01-12', NULL, 'Deep Impact', 'Comet', 'http://www.nasa.gov/content/nasa-the-deep-impact-spacecraft/', 'nasa,jpl');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(74, 'no15', 'active', '1998-05-13', 'NOAA', 'NOAA 15', 'Earth', 'http://www.goes.noaa.gov/', 'noaa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(75, 'tdr7', 'active', '1995-07-13', 'TDRS', 'TDRS 7 - Tracking and Data Relay Satellite', 'Earth', 'http://tdrs.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(76, 'ch1', 'silent', '2008-10-22', NULL, 'Chandrayaan', 'Moon', 'http://www.isro.gov.in/Spacecraft/chandrayaan-1', 'isro');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(77, 'mro', 'active', '2005-08-12', NULL, 'Mars Reconnaissance Orbiter', 'Mars', 'http://mars.nasa.gov/mro/', 'nasa,jpl');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(78, 'mvn', 'active', '2013-11-18', NULL, 'MAVEN', 'Mars', 'http://mars.nasa.gov/maven/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(79, 'cass', 'active', '1997-10-15', NULL, 'Cassini', 'Saturn', 'http://saturn.jpl.nasa.gov/', 'nasa,esa,jpl,asi');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(80, 'sele', 'dead', '2007-09-14', NULL, 'Kaguya - SELENE', 'Moon', 'http://www.kaguya.jaxa.jp/index_e.htm', 'jaxa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(81, 'stab', 'active', '2006-10-26', 'STEREO', 'STEREO B', 'Heliocentric', 'http://stereo.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(82, 'td10', 'active', '2002-12-05', 'TDRS', 'TDRS 10 - Tracking and Data Relay Satellite', 'Earth', 'http://tdrs.gsfc.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(83, 'kepl', 'active', '2009-03-07', NULL, 'Kepler', 'Heliocentric', 'http://kepler.nasa.gov/', 'nasa,lasp');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(84, 'terr', 'active', '1999-12-18', NULL, 'TERRA', 'Earth', 'http://terra.nasa.gov/', 'nasa');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(85, 'lcro', 'dead', '2009-06-18', NULL, 'LCROSS - Lunar CRater Observation and Sensing Satellite', 'Moon', 'http://lcross.arc.nasa.gov/', 'nasa,arc');
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(86, 'PRCN', 'active', '2014-12-03', NULL, 'PROCYON', 'Asteroid belt', 'https://directory.eoportal.org/web/eoportal/satellite-missions/p/procyon', 'jaxa');
# @added 20160902 - New spacecraft seen - OSIRIS-REx
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(87, 'orx', 'active', '2016-09-08', NULL, 'OSIRIS-REx', 'Heliocentric', 'http://www.nasa.gov/osiris-rex, http://www.asteroidmission.org/', 'nasa');
# @added 20161016 - As per https://github.com/earthgecko/pydsn/issues/2 - Add Trace Gas Orbiter (TGO)
INSERT INTO `extSpacecraft` (`ID`, `name`, `status`, `launch`, `constellation`, `friendlyName`, `location`, `url`, `agency`) VALUES(143, 'tgo', 'active', '2016-09-10', NULL, 'Trace Gas Orbiter', 'Mars', 'http://sci.esa.int/mars-express/', 'esa');

# @added 20160903 - Feature #1624: tweets table
CREATE TABLE `tweets` (
  `ID` mediumint unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(20) NOT NULL,  # Account that tweeted
  `tweet` varchar(140) NOT NULL,
  `created` date DEFAULT NULL,
  `uri` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`ID`),
  KEY `tweets` (`name`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8;
