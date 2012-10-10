CREATE TABLE `agendaitems` (
  `agendaitem_id` int(11) unsigned NOT NULL,
  `session_id` int(10) unsigned default NULL,
  `agendaitem_identifier` varchar(255) default NULL,
  `agendaitem_public` tinyint(1) unsigned default NULL,
  `agendaitem_subject` mediumtext,
  `agendaitem_result` varchar(255) default NULL,
  PRIMARY KEY  (`agendaitem_id`),
  KEY `session_id` (`session_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `agendaitems2attachments` (
  `agendaitem_id` int(11) unsigned NOT NULL,
  `attachment_id` int(10) unsigned NOT NULL,
  `attachment_role` varchar(255) default NULL,
  UNIQUE KEY `agendaitem_id` (`agendaitem_id`,`attachment_id`,`attachment_role`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `agendaitems2requests` (
  `agendaitem_id` int(11) unsigned NOT NULL,
  `request_id` int(11) unsigned NOT NULL,
  UNIQUE KEY `agendaitem_id` (`agendaitem_id`,`request_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `agendaitems2submissions` (
  `agendaitem_id` int(11) unsigned NOT NULL,
  `submission_id` int(10) unsigned NOT NULL,
  UNIQUE KEY `agendaitem_id` (`agendaitem_id`,`submission_id`),
  KEY `agendaitem_id_2` (`agendaitem_id`),
  KEY `submission_id` (`submission_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `attachments` (
  `attachment_id` int(11) unsigned NOT NULL default '0',
  `attachment_mimetype` varchar(255) default NULL,
  `attachment_filename` varchar(255) default NULL,
  `attachment_size` int(11) default NULL,
  `sha1_checksum` varchar(40) default NULL,
  `attachment_content` longtext,
  `attachment_lastmod` datetime default NULL,
  PRIMARY KEY  (`attachment_id`),
  KEY `sha1_checksum` (`sha1_checksum`),
  KEY `attachment_lastmod` (`attachment_lastmod`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `attendance` (
  `person_id` int(11) unsigned default NULL,
  `session_id` int(11) unsigned default NULL,
  `attendance_function` varchar(255) default NULL,
  UNIQUE KEY `session_id_2` (`session_id`,`person_id`),
  KEY `person_id` (`person_id`),
  KEY `session_id` (`session_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `committees` (
  `committee_id` int(11) unsigned NOT NULL default '0',
  `committee_title` varchar(255) default NULL,
  PRIMARY KEY  (`committee_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `people` (
  `person_id` int(11) unsigned NOT NULL default '0',
  `person_name` varchar(255) default NULL,
  `person_organization` varchar(255) default NULL,
  PRIMARY KEY  (`person_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `requests` (
  `request_id` int(11) unsigned NOT NULL default '0',
  `committee_id` int(11) unsigned default NULL,
  `request_date` date default NULL,
  `request_identifier` varchar(255) default NULL,
  `request_subject` text,
  PRIMARY KEY  (`request_id`),
  KEY `committee_id` (`committee_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `requests2attachments` (
  `request_id` int(11) unsigned NOT NULL,
  `attachment_id` int(11) unsigned NOT NULL,
  `attachment_role` varchar(255) default NULL,
  UNIQUE KEY `attachment_id` (`attachment_id`,`request_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `sessions` (
  `session_id` int(11) unsigned NOT NULL default '0',
  `session_identifier` varchar(255) default NULL,
  `session_date` date default NULL,
  `session_time_start` time default NULL,
  `session_time_end` time default NULL,
  `session_location` varchar(255) default NULL,
  `session_title` varchar(255) default NULL,
  `session_description` varchar(255) default NULL,
  `committee_id` int(11) unsigned default NULL,
  PRIMARY KEY  (`session_id`),
  KEY `session_date` (`session_date`),
  KEY `session_time_start` (`session_time_start`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `sessions2attachments` (
  `session_id` int(11) unsigned NOT NULL,
  `attachment_id` int(11) unsigned NOT NULL,
  `attachment_role` varchar(255) default NULL,
  UNIQUE KEY `session_id` (`session_id`,`attachment_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `submissions` (
  `submission_id` int(11) unsigned NOT NULL default '0',
  `submission_date` date default NULL,
  `submission_identifier` varchar(255) default NULL,
  `submission_type` varchar(255) default NULL,
  `submission_subject` text,
  PRIMARY KEY  (`submission_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `submissions2attachments` (
  `submission_id` int(11) unsigned NOT NULL,
  `attachment_id` int(11) unsigned NOT NULL,
  `attachment_role` varchar(255) default NULL,
  UNIQUE KEY `attachment_id` (`attachment_id`,`submission_id`),
  KEY `submission_id` (`submission_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
