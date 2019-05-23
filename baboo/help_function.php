<?php
  /*
  POST: accepts encoded json string from python bot. guarantees compatibility of provided json
  and adds it to file.
  */

  ini_set("display_errors", 1);
  ini_set("display_startup_errors", 1);
  error_reporting(E_ALL);

  header("Content-type: application/json");

  if (isset($_GET["mode"])) {
    $mode = $_GET["mode"];
    if ($mode == "help") {
      return_json();
    } else {
      header("HTTP/1.1 - 400 Invalid Request");
      echo json_encode(array("Success" => False, "data" => "Error: Invalid mode."));
    }
  } else {

    $json = file_get_contents("php://input");

    if (strlen($json) > 0) {
      verify_json($json);
    } else {
      header("HTTP/1.1 - 400 Invalid Request");
      echo json_encode(array("Success" => False, "data" => "Error: Data not included."));
    }
  }


  function verify_json($json) {
    $test = json_decode($json);  // remove later
    if (isset($test)) {
      file_put_contents("help_contents.json", $json);
      echo json_encode(array("Success" => True));
    } else {
      header("HTTP/1.1 - 400 Invalid Request");
      echo json_encode(array("Success" => False, "data" => "Error: JSON failed to parse."));
    }
  }

  function return_json() {
    echo file_get_contents("help_contents.json");
  }
?>
