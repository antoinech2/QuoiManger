<?php

header("Content-Type: application/json");

$data=$_POST;
$json=json_encode($data);
echo $json;

?>
