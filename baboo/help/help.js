"use strict";

(function() {

  function gen(tag) {
    return document.createElement(tag);
  }

  function id(str) {
    return document.getElementById(str);
  }

  function makePromise(url, method = "GET") {
    let xhr = new XMLHttpRequest();
    let prom = new Promise(function(res, rej) {

      xhr.addEventListener("readystatechange", function() {
        if (xhr.readyState === 4) {
          if (xhr.status >= 200 && xhr.status < 300) {
            res(xhr.responseText);
          } else {
            rej({
              status: xhr.status,
              resp: xhr.responseText
            });
          }
        }
      });
      xhr.open(method, url, true);
      xhr.send();
    });

    return prom;
  }

  function populateHelpContents(jsonFuncs) {
    let parent = id("help-container");
    for (let func of jsonFuncs) {
      let body = gen("section");

      if (func.module === "NSFW") {
        body.classList.add("nsfw");
      }

      let title = gen("h2");
      title.innerText = func.name;

      let descrip = gen("p");
      descrip.innerText = func.descrip;

      let aliasList = gen("ul");
      for (let i = 0; i < func.aliases.length; i++) {
        let alias = gen("li");
        alias.innerText = func.aliases[i];
        aliasList.appendChild(alias);
      }

      let moduleFooter = gen("footer");

      let moduleFooterText = gen("p");
      let moduleName = gen("span");

      moduleFooterText.innerText = "Module: ";
      moduleName.innerText = func.module;

      moduleFooterText.appendChild(moduleName);

      moduleFooter.appendChild(moduleFooterText);

      body.appendChild(title);
      body.appendChild(descrip);
      body.appendChild(aliasList);
      body.appendChild(moduleFooter);

      parent.appendChild(body);

      console.log(`Added ${func.title} to container.`);
    }
  }

  function init() {
    makePromise("../help_contents.json")
      .then(JSON.parse)
      .then(populateHelpContents)
      .catch(console.error);
    document.querySelector("input").addEventListener("input", updateHelpTabs);
  }

  function updateHelpTabs() {
    let str = this.value.toLowerCase();

    let helpList = document.querySelectorAll("#help-container section");

    for (let func of helpList) {
      let name = func.querySelector("h2").innerText.toLowerCase();
      let descrip = func.querySelector("p").innerText.toLowerCase();
      let module = func.querySelector("footer p span").innerText.toLowerCase();
      if (name.indexOf(str) !== -1 || module.indexOf(str) !== -1) {
        func.classList.remove("intangible", "halfopac");
      } else if (descrip.indexOf(str) !== -1) {
        func.classList.remove("intangible");
        func.classList.add("halfopac");
      } else {
        func.classList.add("intangible");
      }
    }
  }

  window.addEventListener("load", init);

}());
