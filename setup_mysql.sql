CREATE TABLE `attachments` (
  `attachment_id` int(11) NOT NULL DEFAULT '0',
  `attachment_mimetype` varchar(255) DEFAULT NULL,
  `attachment_filename` varchar(255) DEFAULT NULL,
  `attachment_size` int(11) DEFAULT NULL,
  `attachment_content` text,
  PRIMARY KEY (`attachment_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `attendance` (
  `person_id` int(11) DEFAULT NULL,
  `session_id` int(11) DEFAULT NULL,
  `attendance_function` varchar(255) DEFAULT NULL,
  UNIQUE KEY `session_id_2` (`session_id`,`person_id`),
  KEY `person_id` (`person_id`),
  KEY `session_id` (`session_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `committees` (
  `committee_id` int(11) NOT NULL DEFAULT '0',
  `committee_title` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`committee_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `people` (
  `person_id` int(11) NOT NULL DEFAULT '0',
  `person_name` varchar(255) DEFAULT NULL,
  `person_organization` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`person_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `requests` (
  `request_id` int(11) NOT NULL DEFAULT '0',
  `committees` varchar(255) DEFAULT NULL,
  `request_date` date DEFAULT NULL,
  `request_identifier` varchar(255) DEFAULT NULL,
  `request_subject` varchar(255) DEFAULT NULL,
  `attachment_ids` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`request_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `sessions` (
  `session_id` int(11) NOT NULL DEFAULT '0',
  `session_identifier` varchar(255) DEFAULT NULL,
  `session_date` date DEFAULT NULL,
  `session_time_start` time DEFAULT NULL,
  `session_time_end` time DEFAULT NULL,
  `session_location` varchar(255) DEFAULT NULL,
  `session_title` varchar(255) DEFAULT NULL,
  `session_description` varchar(255) DEFAULT NULL,
  `committee_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`session_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

CREATE TABLE `submissions` (
  `submission_id` int(11) NOT NULL DEFAULT '0',
  `submission_date` date DEFAULT NULL,
  `submission_identifier` varchar(255) DEFAULT NULL,
  `submission_type` varchar(255) DEFAULT NULL,
  `submission_subject` varchar(255) DEFAULT NULL,
  `attachment_ids` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`submission_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
