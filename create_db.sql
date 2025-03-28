-- -----------------------------------------------------
-- Schema macdb
-- -----------------------------------------------------

-- -----------------------------------------------------
-- Table `user`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `user` (
  `user_id` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(45) NOT NULL,
  `email` VARCHAR(200) NOT NULL,
  `password_hash` VARCHAR(64) NOT NULL,
  `first_name` VARCHAR(45) NOT NULL,
  `last_name` VARCHAR(45) NOT NULL,
  `location` VARCHAR(45) NOT NULL,
  `description` VARCHAR(255) NULL,
  `profile_image` VARCHAR(255) NULL,
  `role` ENUM('voter', 'admin', 'helper') NOT NULL DEFAULT 'voter',
  `status` ENUM('active', 'inactive') NOT NULL DEFAULT 'active',
  `public` ENUM('visible', 'hidden') NOT NULL DEFAULT 'visible',
  `message_board` ENUM('allowed', 'banned') NOT NULL DEFAULT 'allowed',
  PRIMARY KEY (`user_id`),
  UNIQUE INDEX `email_UNIQUE` (`email` ASC) VISIBLE,
  UNIQUE INDEX `username_UNIQUE` (`username` ASC) VISIBLE)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `competition_application`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `competition_application` (
  `application_id` INT NOT NULL AUTO_INCREMENT,
  `proposer_id` INT NOT NULL,
  `theme` VARCHAR(255) NOT NULL,
  `description` VARCHAR(2000) NOT NULL,
  `status` ENUM('pending', 'approved', 'declined') NOT NULL DEFAULT 'pending',
  `create_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `type` ENUM('create', 'delete') NOT NULL DEFAULT 'create',
  `competition_id_delete` INT NULL,
  PRIMARY KEY (`application_id`),
  INDEX `proposer_idx` (`proposer_id` ASC) VISIBLE,
  CONSTRAINT `FK_competition_proposer_id`
    FOREIGN KEY (`proposer_id`)
    REFERENCES `user` (`user_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `competition`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `competition` (
  `competition_id` INT NOT NULL AUTO_INCREMENT,
  `application_id` INT NOT NULL,
  `status` ENUM('open', 'nomsg', 'archive') NOT NULL DEFAULT 'open',
  PRIMARY KEY (`competition_id`),
  INDEX `application_id_idx` (`application_id` ASC) VISIBLE,
  CONSTRAINT `application_id`
    FOREIGN KEY (`application_id`)
    REFERENCES `competition_application` (`application_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `event`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `event` (
  `event_id` INT NOT NULL AUTO_INCREMENT,
  `competition_id` INT NOT NULL,
  `start_date` DATE NOT NULL,
  `end_date` DATE NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `description` VARCHAR(1000) NOT NULL,
  `image` VARCHAR(255) NOT NULL,
  `status` ENUM('plan', 'current', 'unfinal', 'final', 'ban') NOT NULL DEFAULT 'plan',
  PRIMARY KEY (`event_id`),
  INDEX `competition_idx` (`competition_id` ASC) VISIBLE,
  CONSTRAINT `competition`
    FOREIGN KEY (`competition_id`)
    REFERENCES `competition` (`competition_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `competitor`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `competitor` (
  `competitor_id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(100) NOT NULL,
  `description` VARCHAR(1000) NOT NULL,
  `image` VARCHAR(255) NOT NULL,
  PRIMARY KEY (`competitor_id`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `candidate`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `candidate` (
  `candidate_id` INT NOT NULL AUTO_INCREMENT,
  `competition_id` INT NOT NULL,
  `competitor_id` INT NOT NULL,
  `event_id` INT NOT NULL,
  INDEX `FK_manage_competitor_idx` (`competitor_id` ASC) VISIBLE,
  INDEX `FK_manage_event_idx` (`event_id` ASC) VISIBLE,
  PRIMARY KEY (`candidate_id`),
  INDEX `FK_manage_competition_idx` (`competition_id` ASC) VISIBLE,
  CONSTRAINT `FK_manage_competition`
    FOREIGN KEY (`competition_id`)
    REFERENCES `competition` (`competition_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `FK_manage_competitor`
    FOREIGN KEY (`competitor_id`)
    REFERENCES `competitor` (`competitor_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `FK_manage_event`
    FOREIGN KEY (`event_id`)
    REFERENCES `event` (`event_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `vote`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `vote` (
  `vote_id` INT NOT NULL AUTO_INCREMENT,
  `voter_id` INT NOT NULL,
  `candidate_id` INT NOT NULL,
  `ip_address` VARCHAR(255) NOT NULL,
  `create_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `status` ENUM('valid', 'invalid') NOT NULL DEFAULT 'valid',
  PRIMARY KEY (`vote_id`),
  INDEX `voter_idx` (`voter_id` ASC) VISIBLE,
  INDEX `FK_vote_candidate_id_idx` (`candidate_id` ASC) VISIBLE,
  CONSTRAINT `FK_vote_voter_id`
    FOREIGN KEY (`voter_id`)
    REFERENCES `user` (`user_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `FK_vote_candidate_id`
    FOREIGN KEY (`candidate_id`)
    REFERENCES `candidate` (`candidate_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `result`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `result` (
  `result_id` INT NOT NULL AUTO_INCREMENT,
  `candidate_id` INT NOT NULL,
  `total_votes` INT NOT NULL,
  `percentage` DECIMAL(4,2) NOT NULL,
  PRIMARY KEY (`result_id`),
  INDEX `FK_result_candidate_id_idx` (`candidate_id` ASC) VISIBLE,
  CONSTRAINT `FK_result_candidate_id`
    FOREIGN KEY (`candidate_id`)
    REFERENCES `candidate` (`candidate_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `staff`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `staff` (
  `competition_id` INT NOT NULL,
  `user_id` INT NOT NULL,
  `role` ENUM('cadmin', 'cscrutineer', 'cmoderator') NOT NULL,
  PRIMARY KEY (`competition_id`, `user_id`),
  INDEX `FK_cadmin_user_id_idx` (`user_id` ASC) VISIBLE,
  CONSTRAINT `FK_cadmim_competition)id`
    FOREIGN KEY (`competition_id`)
    REFERENCES `competition` (`competition_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `FK_cadmin_user_id`
    FOREIGN KEY (`user_id`)
    REFERENCES `user` (`user_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `announcement`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `announcement` (
  `announcement_id` INT NOT NULL AUTO_INCREMENT,
  `announcer_id` INT NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `content` VARCHAR(1000) NOT NULL,
  `create_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `competition_id` INT NULL,
  `type` ENUM('global', 'competition') NOT NULL,
  PRIMARY KEY (`announcement_id`),
  INDEX `FK_announcement_announcer_id_idx` (`announcer_id` ASC) VISIBLE,
  CONSTRAINT `FK_announcement_announcer_id`
    FOREIGN KEY (`announcer_id`)
    REFERENCES `user` (`user_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `donation_application`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `donation_application` (
  `application_id` INT NOT NULL AUTO_INCREMENT,
  `competition_id` INT NOT NULL,
  `proposer_id` INT NOT NULL,
  `charity_name` VARCHAR(255) NOT NULL,
  `charity_id` VARCHAR(20) NOT NULL,
  `ird` VARCHAR(45) NOT NULL,
  `bank_account` VARCHAR(50) NOT NULL,
  `description` VARCHAR(1000) NOT NULL,
  `goal` DECIMAL(12,2) NOT NULL,
  `start_date` DATE NOT NULL,
  `status` ENUM('pending', 'approved', 'declined') NOT NULL DEFAULT 'pending',
  `create_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`application_id`),
  INDEX `FK_donation_proposer_id_idx` (`proposer_id` ASC) VISIBLE,
  INDEX `FK_donation_application_competition_id_idx` (`competition_id` ASC) VISIBLE,
  CONSTRAINT `FK_donation_application_competition_id`
    FOREIGN KEY (`competition_id`)
    REFERENCES `competition` (`competition_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `FK_donation_application_proposer_id`
    FOREIGN KEY (`proposer_id`)
    REFERENCES `user` (`user_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `donation`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `donation` (
  `donation_id` INT NOT NULL,
  `competition_id` INT NOT NULL,
  `total_raised` DECIMAL(12,2) NOT NULL,
  `percentage` DECIMAL(6,4) NOT NULL,
  `status` ENUM('current', 'finished', 'ban') NOT NULL DEFAULT 'current',
  PRIMARY KEY (`donation_id`),
  INDEX `FK_donation_application_competition_idx` (`competition_id` ASC) VISIBLE,
  CONSTRAINT `FK_donation_application_competition`
    FOREIGN KEY (`competition_id`)
    REFERENCES `competition` (`competition_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `donation_record`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `donation_record` (
  `record_id` INT NOT NULL AUTO_INCREMENT,
  `donation_id` INT NOT NULL,
  `donor_id` INT NOT NULL,
  `amount` DECIMAL(12,2) NOT NULL,
  `anonymous` ENUM('no', 'yes') NOT NULL DEFAULT 'no',
  `create_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`record_id`),
  INDEX `FK_donation_record_donation_id_idx` (`donation_id` ASC) VISIBLE,
  INDEX `FK_donation_record_doner_idx` (`donor_id` ASC) VISIBLE,
  CONSTRAINT `FK_donation_record_donation_id`
    FOREIGN KEY (`donation_id`)
    REFERENCES `donation` (`donation_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `FK_donation_record_doner`
    FOREIGN KEY (`donor_id`)
    REFERENCES `user` (`user_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `message`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `message` (
  `message_id` INT NOT NULL AUTO_INCREMENT,
  `sender_id` INT NOT NULL,
  `competition_id` INT NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `content` VARCHAR(255) NOT NULL,
  `create_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `type` ENUM('normal', 'hot') NOT NULL DEFAULT 'normal',
  `like` INT NOT NULL DEFAULT 0,
  PRIMARY KEY (`message_id`),
  INDEX `FK_message_sender_id_idx` (`sender_id` ASC) VISIBLE,
  INDEX `FK_message_competition_id_idx` (`competition_id` ASC) VISIBLE,
  CONSTRAINT `FK_message_sender_id`
    FOREIGN KEY (`sender_id`)
    REFERENCES `user` (`user_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `FK_message_competition_id`
    FOREIGN KEY (`competition_id`)
    REFERENCES `competition` (`competition_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `reply`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `reply` (
  `reply_id` INT NOT NULL AUTO_INCREMENT,
  `sender_id` INT NOT NULL,
  `message_id` INT NOT NULL,
  `content` VARCHAR(255) NOT NULL,
  `create_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`reply_id`),
  INDEX `FK_reply_sender_id_idx` (`sender_id` ASC) VISIBLE,
  INDEX `FK_reply_message_id_idx` (`message_id` ASC) VISIBLE,
  CONSTRAINT `FK_reply_sender_id`
    FOREIGN KEY (`sender_id`)
    REFERENCES `user` (`user_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `FK_reply_message_id`
    FOREIGN KEY (`message_id`)
    REFERENCES `message` (`message_id`)
    ON DELETE CASCADE
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `request`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `request` (
  `request_id` INT NOT NULL AUTO_INCREMENT,
  `proposer_id` INT NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `description` VARCHAR(1000) NOT NULL,
  `status` ENUM('new', 'open', 'resolved') NOT NULL DEFAULT 'new',
  `create_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`request_id`),
  INDEX `FK_request_requester_id_idx` (`proposer_id` ASC) VISIBLE,
  CONSTRAINT `FK_request_requester_id`
    FOREIGN KEY (`proposer_id`)
    REFERENCES `user` (`user_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `request_message`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `request_message` (
  `message_id` INT NOT NULL AUTO_INCREMENT,
  `sender_id` INT NOT NULL,
  `request_id` INT NOT NULL,
  `content` VARCHAR(1000) NOT NULL,
  `create_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`message_id`),
  INDEX `FK_request_message_sander_id_idx` (`sender_id` ASC) VISIBLE,
  INDEX `FK_request_message_request_id_idx` (`request_id` ASC) VISIBLE,
  CONSTRAINT `FK_request_message_sander_id`
    FOREIGN KEY (`sender_id`)
    REFERENCES `user` (`user_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `FK_request_message_request_id`
    FOREIGN KEY (`request_id`)
    REFERENCES `request` (`request_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `competition_approval`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `competition_approval` (
  `approval_id` INT NOT NULL AUTO_INCREMENT,
  `application_id` INT NOT NULL,
  `approver_id` INT NOT NULL,
  `approval_status` ENUM('approved', 'declined') NOT NULL,
  `feedback` VARCHAR(255) NULL,
  `create_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`approval_id`),
  INDEX `competition_id_idx` (`application_id` ASC) VISIBLE,
  INDEX `approver_id_idx` (`approver_id` ASC) VISIBLE,
  CONSTRAINT `competition_id`
    FOREIGN KEY (`application_id`)
    REFERENCES `competition_application` (`application_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `approver_id`
    FOREIGN KEY (`approver_id`)
    REFERENCES `user` (`user_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `customer_service`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `customer_service` (
  `service_id` INT NOT NULL AUTO_INCREMENT,
  `helper_id` INT NOT NULL,
  `request_id` INT NOT NULL,
  `status` ENUM('open', 'resolved', 'drop') NOT NULL,
  `create_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`service_id`),
  INDEX `request_id_idx` (`request_id` ASC) VISIBLE,
  INDEX `helper_id_idx` (`helper_id` ASC) VISIBLE,
  CONSTRAINT `request_id`
    FOREIGN KEY (`request_id`)
    REFERENCES `request` (`request_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `helper_id`
    FOREIGN KEY (`helper_id`)
    REFERENCES `user` (`user_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `donation_approval`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `donation_approval` (
  `approval_id` INT NOT NULL AUTO_INCREMENT,
  `application_id` INT NOT NULL,
  `approver_id` INT NOT NULL,
  `status` ENUM('approved', 'declined') NOT NULL,
  `feedback` VARCHAR(255) NULL,
  `create_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`approval_id`),
  INDEX `application_id_idx` (`application_id` ASC) VISIBLE,
  INDEX `approver_id_idx` (`approver_id` ASC) VISIBLE,
  CONSTRAINT `FK_donation_approval_application_id`
    FOREIGN KEY (`application_id`)
    REFERENCES `donation_application` (`application_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `FK_donation_approval_approver_id`
    FOREIGN KEY (`approver_id`)
    REFERENCES `user` (`user_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `payment`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `payment` (
  `payment_id` INT NOT NULL AUTO_INCREMENT,
  `payment_method` ENUM('card', 'transfer') NOT NULL,
  `payment_amount` DECIMAL(12,2) NOT NULL,
  `create_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `payment_status` ENUM('successful', 'failed') NOT NULL,
  INDEX `FK_payment_donation_record_idx` (`payment_id` ASC) VISIBLE,
  PRIMARY KEY (`payment_id`),
  CONSTRAINT `FK_payment_donation_record`
    FOREIGN KEY (`payment_id`)
    REFERENCES `donation_record` (`record_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `user_like_msg`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `user_like_msg` (
  `message_id` INT NOT NULL,
  `user_id` INT NOT NULL,
  INDEX `FK_message_message_id_idx` (`message_id` ASC) VISIBLE,
  INDEX `FK_message_user_id_idx` (`user_id` ASC) VISIBLE,
  CONSTRAINT `FK_message_message_id`
    FOREIGN KEY (`message_id`)
    REFERENCES `message` (`message_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `FK_message_user_id`
    FOREIGN KEY (`user_id`)
    REFERENCES `user` (`user_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `pay_card`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `pay_card` (
  `payment_id` INT NOT NULL,
  `card_number` VARCHAR(45) NOT NULL,
  `expires` VARCHAR(5) NOT NULL,
  `cvv` VARCHAR(3) NOT NULL,
  `cardholder` VARCHAR(45) NOT NULL,
  INDEX `FK_pay_card_payment_id_idx` (`payment_id` ASC) VISIBLE,
  CONSTRAINT `FK_pay_card_payment_id`
    FOREIGN KEY (`payment_id`)
    REFERENCES `payment` (`payment_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `pay_transfer`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `pay_transfer` (
  `payment_id` INT NOT NULL,
  `payee` VARCHAR(50) NOT NULL,
  `account_number` VARCHAR(50) NOT NULL,
  INDEX `FK_pay_transfer_payment_id_idx` (`payment_id` ASC) VISIBLE,
  CONSTRAINT `FK_pay_transfer_payment_id`
    FOREIGN KEY (`payment_id`)
    REFERENCES `payment` (`payment_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;