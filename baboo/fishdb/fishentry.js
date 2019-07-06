"use strict";

(function() {

  window.addEventListener("load", init);

  function init() {
    console.log("init");
    document.querySelector("button").addEventListener("click", submitFish);
    document.querySelector("textarea").addEventListener("focus", wipeTextarea);
  }

  function wipeTextarea() {
    this.value = "";
    this.removeEventListener("focus", wipeTextarea);
  }

  function fqs(string) {
    return document.querySelector("div " + string);
  }

  function submitFish() {

    let submission = {
      name: fqs("input[name='fishname']").value,
      description: fqs("textarea").value,
      location: fqs("select").value,
      sizelow: fqs("input[name='sizelow']").value,
      sizehigh: fqs("input[name='sizehigh']").value,
      weight: fqs("input[name='weight']").value
    };

    let url = "http://baboo.mobi/government/fishdb/fishentry.php?";
    for (let key in submission) {
      url += key + "=" + submission[key] + "&";
    }
    url = url.substring(0, url.length - 1); // hehe
    console.log(url);
    fetch(url)
      .then(checkStatus)
      .then(refreshSubmit)
      .catch(refreshSubmit);
  }

  function checkStatus(response) {
    if (response.status >= 200 && response.status < 300) {
      return response.text();
    } else {
      return response.text().then(Promise.reject.bind(Promise));
    }
  }

  function refreshSubmit(text) {
    document.querySelector("h1").innerText = text + ", reloading...";
    setTimeout(() => location.reload(), 3000);

  }

})();
