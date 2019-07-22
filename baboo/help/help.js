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

      xhr.addEventListener("readyStateChange", function() {
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

      console.log("Added ${func.title} to container.");
    }
  }

  const json = `[{"name": "coinflip", "descrip": "Flips a coin that you can watch tumble in the air.\n\nUsage:\ng coinflip", "aliases": ["flip"], "module": "Fun"}, {"name": "8ball", "descrip": "Funny little 8ball game for you and friends.", "aliases": [], "module": "Fun"}, {"name": "fortune", "descrip": "Tells your fortune. One fortune per day.\n\nUsage:\ng fortune", "aliases": [], "module": "Fun"}, {"name": "help", "descrip": "No description available.", "aliases": [], "module": "Fun"}, {"name": "night", "descrip": "No description available.", "aliases": [], "module": "Fun"}, {"name": "poll", "descrip": "Run a poll in your current server.\n\nUsage:\ng poll <question> <duration int (seconds)> <choiceA> | <choiceB> | ...\n\nBot will send reminder messages every few, with a link to the message.\n\nPrints the final results at the end of the poll!", "aliases": [], "module": "Fun"}, {"name": "pushup", "descrip": "A contest of wits.\n\nUsage:\ng pushup <int>", "aliases": [], "module": "Fun"}, {"name": "roll", "descrip": "Operators are added automatically, separated by spaces.\nUsage:\ng roll [dice1, dice2, ...]\n\nDice are specified as <number>d<sides>. Modifiers are provided as positive or negative integers: +4 = 4, -3 = -3.\n\nExample:\ng roll 3d6 2d20 -3 - three six-sided die + two 20-sided die - 3", "aliases": [], "module": "Fun"}, {"name": "trivia", "descrip": "Play a funky trivia game with your friends.\n\nUsage: g trivia", "aliases": [], "module": "Fun"}, {"name": "uptime", "descrip": "No description available.", "aliases": [], "module": "Fun"}, {"name": "e621", "descrip": "Grabs images from e621.net. Tags are separated by white space, all valid tags are supported.\n\nOptional page count parameter if you're out of the good stuff. Defaults to page 1.\n\nUsage:\ng e621 [tag1 tag2 ... tag6] (page<int>)", "aliases": [], "module": "NSFW"}, {"name": "rule34", "descrip": "Grabs images from rule34.xxx. Tags separated by white space, all valid tags are supported.\n\nOptional pagenum parameter fetches more stuff if you're thirsting for the flesh.\n\nUsage:\ng rule34 [tag1 tag2 tag3 ... tag6] (page<int>)", "aliases": [], "module": "NSFW"}, {"name": "steamid", "descrip": "Look up a friend!\n\nUsage:\ng steamid (<vanityurl> or <steamid>)", "aliases": [], "module": "Steam"}, {"name": "board", "descrip": "See who's killing it locally.\n\nUsage:\ng board", "aliases": [], "module": "Stattrack"}, {"name": "rank", "descrip": "Displays an embedded summary of your history as a user, or the history of another user.\n\nUsage:\ng rank <user mention>", "aliases": [], "module": "Stattrack"}, {"name": "playing", "descrip": "Returns information on the video currently playing on the bot in a given server.\n\nReturns a default message if nothing is playing.\n\nUsage:\ng playing", "aliases": [], "module": "Player"}, {"name": "pause", "descrip": "Pauses currently playing video. Only works if the bot is already in a call.\n\nUsage:\ng pause", "aliases": [], "module": "Player"}, {"name": "play", "descrip": "Bot will sing a song for you.\n\nSometimes fails to fetch music, since Youtube blocks content ID'd videos on the bot. We're working on it.\n\nFetches a link if provided, otherwise searches the query on Youtube.\n\nIf paused, resumes playback.\n\nUsage:\ng play (<valid URL> or <search query>)", "aliases": [], "module": "Player"}, {"name": "skip", "descrip": "Submits a skip request to the bot.\n\nIf user is an administrator, the skip is processed immediately.\nOtherwise it's added to a vote tally of users. Once the majority of users in the call votes to skip, the video is skipped.\n\nUsage:\ng skip", "aliases": [], "module": "Player"}, {"name": "stop", "descrip": "Administrator only. Stops current playback, if playing.\n\nUsage:\ng stop", "aliases": [], "module": "Player"}, {"name": "crunch", "descrip": "Naive seam carving (Content aware scale) algorithm with JPEG filter.\n\nUsage:\ng crunch (<url> or ignore if uploaded image) [<crunch amount(0.2)>]", "aliases": [], "module": "ImageModule"}, {"name": "invert", "descrip": "Invert the colors.\n\nUsage:\ng invert (<url> or ignore if uploaded image)", "aliases": [], "module": "ImageModule"}, {"name": "jpeg", "descrip": "Do I look like I-- no no not doing that.\n\nUsage:\ng jpeg (<url> or ignore if uploaded image)", "aliases": [], "module": "ImageModule"}, {"name": "meme", "descrip": "Make a meme.\n\nUsage:\ng meme (<url> or ignore if uploaded image) (<TEXT> or <TOPTEXT> | <BOTTOMTEXT>)", "aliases": [], "module": "ImageModule"}, {"name": "peterhere", "descrip": "Hey guys, peter here.\n\nUsage:\ng peterhere (<url> or ignore if uploaded image) <text>", "aliases": [], "module": "ImageModule"}, {"name": "pixelsort", "descrip": "Quick pixelsorting function. URL or image upload must be provided.\n\nUsage:\ng pixelsort (<url> or ignore if uploaded image) [<threshold (0.5)> <comparison function (luma)>]", "aliases": [], "module": "ImageModule"}, {"name": "stat", "descrip": "Display your user statistics in an image!\n\nUsage:\ng stat", "aliases": [], "module": "ImageModule"}, {"name": "fish", "descrip": "Initializes a command relating to fishing. The following commands are currently available:\ng fish cast - Casts the fishing line at a chosen location.", "aliases": [], "module": "Fishing"}, {"name": "hangup", "descrip": "Hangs up the phone. Don't worry, the other person won't see it. Alternatively, removes you from the call queue.\n\nUsage:\ng hangup", "aliases": [], "module": "Telephone"}, {"name": "multitrivia", "descrip": "No description available.", "aliases": [], "module": "Telephone"}, {"name": "telephone", "descrip": "Make some new friends across the web. NSFW/SFW channels are separated as well, so go nuts.\n\nUsage:\ng telephone", "aliases": [], "module": "Telephone"}]`;

  function init() {
    // makePromise("../help_contents.json")
    //   .then(JSON.parse)
    //   .then(populateHelpContents)
    //   .catch(console.error);
    let regex = /\n/gi;

    let helpobj = JSON.parse(json.replace(regex, "\\n"));
    populateHelpContents(helpobj);
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
