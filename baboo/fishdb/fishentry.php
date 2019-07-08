<?php

  include "db_token.php";

  if (validate_query()) {
    $pdo = get_PDO();
    $query = 'INSERT INTO fishtemp (name, description, location, size_min_two, size_max_two, catch_weight, rarity) VALUES (:a, :b, :c, :d, :e, :f, :g);';
    $rarity = 1;
    $weight = $_GET['weight'];
    if ($weight < 40) {
      $rarity = 2;
      if ($weight < 10) {
        $rarity = 3;
        if ($weight < 3) {
          $rarity = 4;
          if ($weight < 1) {
            $rarity = 5;
          }
        }
      }
    }
    try {
      $rt = $pdo->prepare($query);
      $rt->execute(array(":a"=>$_GET['name'], ":b"=>$_GET['description'], ":c"=>$_GET['location'], ":d"=>$_GET['sizelow'], ":e"=>$_GET['sizehigh'], ":f"=>$weight, ":g"=>$rarity));
    } catch (PDOException $exc) {
      header("HTTP/1.1 503 Database Error");
      header("Content-type: text/plain");
      die("insert failed");
    }
    header("Content-type: text/plain");
    echo("successful journey");
  } else {
    header("Content-type: text/plain");
    echo("sorry friend you fdorgot");
  }

  function validate_query() {
    $KEY_LIST = ['name', 'description', 'location', 'sizelow', 'sizehigh', 'weight'];
    $valid = true;
    foreach ($KEY_LIST as $key) {
      $valid = ($valid && isset($_GET[$key]));
    }
    return $valid;
  }
?>
