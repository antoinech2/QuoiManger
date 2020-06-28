<?php

include('Webhook.php');
$args = ['projectId' => 'cuisine-bae54'];
$wh = new Webhook($args);
$wh->respond_simpleMessage('Say this out loud', 'Display this text on screen');

?>
