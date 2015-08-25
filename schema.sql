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
  `name` varchar(20) NOT NULL,
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
) ENGINE=MyISAM  DEFAULT CHARSET=utf8;

CREATE TABLE `dataDishLastPos` (
  `configDishID` tinyint unsigned NOT NULL,
  `azimuthAngle` float NOT NULL,
  `elevationAngle` float NOT NULL,
  `windSpeed` float NOT NULL,
  PRIMARY KEY (`configDishID`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `dataDishPos` (
  `ID` int unsigned NOT NULL AUTO_INCREMENT,
  `eventID` mediumint unsigned NOT NULL,
  `configDishID` tinyint unsigned NOT NULL,
  `azimuthAngle` float NOT NULL,
  `elevationAngle` float NOT NULL,
  `windSpeed` float NOT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `time_id` (`eventID`,`configDishID`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8;

CREATE TABLE `dataEvent` (
  `ID` mediumint unsigned NOT NULL AUTO_INCREMENT,
  `time` bigint NOT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `tm` (`time`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8;

CREATE TABLE `dataSignal` (
  `ID` smallint unsigned NOT NULL AUTO_INCREMENT,
  `eventID` mediumint unsigned NOT NULL,
  `dataDishID` smallint unsigned NOT NULL,
  `configDishID` tinyint unsigned NOT NULL,
  `upDown` enum('up','down') NOT NULL,
  `stateID` tinyint unsigned NOT NULL,
  `configSpacecraftID` smallint unsigned NOT NULL,
  `flags` set('slave','master') NOT NULL DEFAULT '',
  PRIMARY KEY (`ID`),
  KEY `sel` (`dataDishID`,`upDown`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8;

CREATE TABLE `dataSignalDet` (
  `ID` int unsigned NOT NULL AUTO_INCREMENT,
  `eventID` mediumint unsigned NOT NULL,
  `dataSignalID` smallint unsigned NOT NULL,
  `dataRate` double DEFAULT NULL,
  `frequency` double DEFAULT NULL,
  `power` double DEFAULT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `signal` (`dataSignalID`,`eventID`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8;

CREATE TABLE `dataSignalLastDet` (
  `dataSignalID` smallint unsigned NOT NULL,
  `dataRate` double DEFAULT NULL,
  `frequency` double DEFAULT NULL,
  `power` double DEFAULT NULL,
  PRIMARY KEY (`dataSignalID`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `dataTarget` (
  `ID` int unsigned NOT NULL AUTO_INCREMENT,
  `eventID` mediumint unsigned NOT NULL,
  `configDishID` tinyint unsigned NOT NULL,
  `configSpacecraftID` smallint unsigned NOT NULL,
  `uplegRange` double NOT NULL,
  `downlegRange` double NOT NULL,
  `rtlt` double NOT NULL,
  PRIMARY KEY (`ID`),
  UNIQUE KEY `time_dish_craft` (`eventID`,`configDishID`,`configSpacecraftID`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8;
