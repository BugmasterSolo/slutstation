/* global mat4 */

"use strict";

// currently: bug on mobile in WGL.

// framebuffer working now -- a bit crunchy but i'll get that figured out soon

(function() {

  // todo: add in color variable and tie it in to all of the intricate function-y bits.


  const lightPos = new Float32Array([2, 2, 5]);
  const GREEN = new Float32Array([0.625, 1, 0.675]);
  const SPHERE_PRIMARY = [-2.5, -0.8, -2];
  const TEXCOORDS = new Float32Array([
    0.0, 0.0,
    0.0, 1.0,
    1.0, 1.0,
    1.0, 0.0
  ]);

  const FACECOORDS = new Float32Array([
    -1.0, -1.0, 1.0,
    -1.0,  1.0, 1.0,
    1.0,   1.0, 1.0,
    1.0,  -1.0, 1.0
  ]);

  const FRAME_PAST_LENGTH = 60;

  let isHeaderAnimating = true;                   // whether or not header animation should continue.
  let isMenuOpen = false;                         // whether or not menu animation should continue. might not be necessary.

  let accentColor = [0.625, 1, 0.675];
  let backgroundColor = [0.109, 0.109, 0.109];
  let arrayWorker;                                // our Ico Sphere generation worker.
  let index;                                      // keeps track of global variables. var indices, matrices, etc.
  let time = 0;                                   // global time -- useful for some onscreen motion
  let p1;                                         // for tracking performance
  let deltaTime;                                  // used to increment time based on delay since last render
  let particleList = [];                          // list of all onscreen particles
  let framePast = new Array(FRAME_PAST_LENGTH);   // displays frame time to user by averaging time on last 60 frames
  let menuTime = 0;                               // tracks time for menu animation

  for (let i = 0; i < FRAME_PAST_LENGTH; i++) {
    framePast[i] = 1000;
  }

  // todo: create some modifier variables here, which will multiply the resolution of the framebuffer dynamically based on performance

  // also: figure out what's going on with the hard lines. I think it has something to do with the stencil buffer
  //        (and frankly it looks alright)

  window.addEventListener("load", init);

  /**
  * Creates the icosphere web worker and passes relevant info to it, before sending the result to the glSetup function.
  */
  function init() {
    animateTitle();

    document.getElementById("header-box").addEventListener("click", openMenu);

    document.documentElement.style.setProperty("--accent", floatToHex(accentColor));
    document.documentElement.style.setProperty("--background", floatToHex(backgroundColor));
    if (!(typeof(Worker) === "function")) {
      throw "Error: Your browser doesn't support web workers.";
    }

    for (let i = 0; i < 60; i++) {
      particleList.push(new Particle(Math.random() * 16 - 8, Math.random() * 4 - 2, Math.random() * 10 - 12));
    }

    arrayWorker = new Worker("icosphere.js");

    arrayWorker.onmessage = function(e) {
      console.log("ok");
      glSetup(e.data);
    };

    arrayWorker.postMessage([
      {
        subdivisions: 2,
        wedge: true
      },
      {
        subdivisions: 1,
        wedge: false
      }
    ]);
  }

  const HEX_ARRAY = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, "A", "B", "C", "D", "E", "F"];

  function floatToHex(col) {
    let str = "#";
    for (let i = 0; i < 3; i++) {
      let int = Math.ceil(col[i] * 255);
      str += (HEX_ARRAY[Math.floor(int / 16)] + HEX_ARRAY[int % 16]);
    }

    return str;
  }

  function resizeCanvas(gl) {
    gl.canvas.width = window.innerWidth;
    gl.canvas.height = window.innerHeight;

    gl.deleteTexture(index.textures.fbtexture);
    gl.deleteTexture(index.textures.fbdepth);

    gl.bindFramebuffer(gl.FRAMEBUFFER, index.textures.framebuffer);

    const fbtex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, fbtex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.canvas.width, gl.canvas.height, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, fbtex, 0);

    index.textures.fbtexture = fbtex;

    const fbdepth = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, fbdepth);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.DEPTH_COMPONENT, gl.canvas.width, gl.canvas.height, 0, gl.DEPTH_COMPONENT, gl.UNSIGNED_SHORT, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.TEXTURE_2D, fbdepth, 0);

    index.textures.fbdepth = fbdepth;

    gl.bindFramebuffer(gl.FRAMEBUFFER, null);

    gl.viewport(0, 0, gl.canvas.width, gl.canvas.height);
    const newPers = mat4.create();
    mat4.perspective(newPers, Math.PI / 8, gl.canvas.width / gl.canvas.height, 0.1, 100);
    index.matrices.proj = newPers;
    SPHERE_PRIMARY[0] = (gl.canvas.width / gl.canvas.height) * -0.95;
  }

  function openMenu() {
    isHeaderAnimating = false;
    // add to animation frame so that it runs explicitly after animateTitle
    requestAnimationFrame(animateMenu);
  }

  const MENU_DROPS = 1.0;  // Time at which menu nodes drop down

  const GROWTH_TIME = 0.5;  // time of animation growth duration (1st phase)

  const SHRINK_TIME = 0.8;  // time of animation shrink duration (2nd phase)

  function animateTitle() {

    if (!isHeaderAnimating) {
      // reassign classes to fit with menu scheme
      let bulletList = document.querySelectorAll(".bullet-node");
      let entries = document.querySelectorAll("nav span");
      let menus = document.querySelectorAll("nav .menu-item");

      for (let bullet of bulletList) {
        bullet.classList.remove("hidden");
        bullet.style.filter = "";
      }

      for (let entry of entries) {
        entry.classList.remove("hidden");
      }

      for (let item of menus) {
        item.classList.add("intangible", "clickable", "menu-unexpand");
      }

      document.querySelector("#highlight-container").remove();
      document.querySelector("#highlight-container-two").remove();
    } else {
      isHeaderAnimating = (isHeaderAnimating && time < Math.max((GROWTH_TIME + SHRINK_TIME), (MENU_DROPS + 2.0)));

      let width = document.querySelector("header h2").getBoundingClientRect().width || 240;  // our sacred fellow

      let divMiddle = document.querySelector("#highlight-container h2.highlight");
      let divFront = document.querySelector("#highlight-container-two h2.highlight");

      let frontWidth = 0;
      let middleWidth = 0;

      frontWidth = Math.max(width - (width * Math.pow((time * (1 / GROWTH_TIME)), 7)), 0);
      middleWidth = Math.max(width - (time > 0.5 ? (Math.pow((time - 0.5) * (1 / SHRINK_TIME), 0.04) * width) : 0), 0);

      divFront.style.width = frontWidth + "px";
      divMiddle.style.width = middleWidth + "px";

      if (time > MENU_DROPS) {
        let bulletList = document.querySelectorAll(".bullet-node");
        for (let i = 0; i < bulletList.length; i++) {
          let timeMod = 1.4 * (time - MENU_DROPS) * Math.PI - i / 1.6;
          let bullet = bulletList[i];
          bullet.style.filter = "opacity(" + 0.6 * (timeMod > 0 && timeMod < Math.PI / 2 ? Math.sin(timeMod) : 0) + ")";
        }
      }

      requestAnimationFrame(animateTitle);
    }
  }

  const MENU_MOTION = 25;
  const MENU_DUR = 0.4;
  const MENU_OFFSET = 0.1;  // add more detailed stuff like this for the others
  const MENU_POWER = 0.1;

  function animateMenu() {
    let items = document.querySelectorAll("nav .menu-item");
    for (let item of items) {
      item.classList.toggle("intangible");
      item.style.marginLeft = -MENU_MOTION + "px";
      item.style.filter = "opacity(0)";
    }
    menuTime = time;
    if (!isMenuOpen) {
      requestAnimationFrame(iterateMenu);
    }
    isMenuOpen = !isMenuOpen;
  }

  function fade(t) {
    return t * t * t * (t * (t * 6 - 15) + 10);
  }


  function iterateMenu() {
    let items = document.querySelectorAll("nav .menu-item");
    let elapsedTime = (time - menuTime);
    for (let i = 0; i < items.length; i++) {
      let phase = Math.min(Math.pow((elapsedTime / MENU_DUR) - (i * MENU_OFFSET), MENU_POWER), 1);
      items[i].style.marginLeft = MENU_MOTION * (phase - 1) + "px";
      items[i].style.filter = "opacity(" + phase + ")";
    }

    if (elapsedTime < (MENU_DUR + (items.length - 1) * MENU_OFFSET)) {
      requestAnimationFrame(iterateMenu);
    }
  }


  function glSetup(response) {
    let gl = document.getElementById("primary-canvas").getContext("webgl");

    let ext = gl.getExtension("WEBGL_debug_renderer_info");
    gl.getExtension("WEBGL_depth_texture");

    /*
    * Necessary in order to get accurate depth out of framebuffer.
    * Doesn't play nicely and seems very wrong.
    * Will have to look into this soon :)
    * ++: renderbuffer use may prove useful
    */

    if (ext) {
      console.log(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL));
      console.log(gl.getParameter(ext.UNMASKED_VENDOR_WEBGL));
    }

    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

    let vertexArray = new Float32Array(response[0].vertices);
    let faceArray = new Uint16Array(response[0].faces);
    let normalArray = new Float32Array(response[0].normals);
    let wedgeNormal = new Float32Array(response[0].wedgeNormal);

    const wedgeprog = compileProgram(gl, id("vertex-wedge").innerText, id("fragment-wedge").innerText);
    const particleprog = compileProgram(gl, id("vertex-particle").innerText, id("fragment-particle").innerText);
    const frameprog = compileProgram(gl, id("vertex-frame").innerText, id("fragment-frame").innerText);

    const fb = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb);

    const fbtex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, fbtex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.canvas.width, gl.canvas.height, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, fbtex, 0);

    const fbdepth = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, fbdepth);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.DEPTH_COMPONENT, gl.canvas.width, gl.canvas.height, 0, gl.DEPTH_COMPONENT, gl.UNSIGNED_SHORT, null);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.TEXTURE_2D, fbdepth, 0);

    gl.bindFramebuffer(gl.FRAMEBUFFER, null);

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, vertexArray, gl.STATIC_DRAW);

    const norm = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, norm);
    gl.bufferData(gl.ARRAY_BUFFER, normalArray, gl.STATIC_DRAW);

    const wNorm = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, wNorm);
    gl.bufferData(gl.ARRAY_BUFFER, wedgeNormal, gl.STATIC_DRAW);

    const el = gl.createBuffer();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, el);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, faceArray, gl.STATIC_DRAW);

    vertexArray = new Float32Array(response[1].vertices);
    faceArray = new Uint16Array(response[1].faces);
    normalArray = new Float32Array(response[1].normals);

    const pbuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, pbuf);
    gl.bufferData(gl.ARRAY_BUFFER, vertexArray, gl.STATIC_DRAW);

    const pnorm = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, pnorm);
    gl.bufferData(gl.ARRAY_BUFFER, normalArray, gl.STATIC_DRAW);

    const pface = gl.createBuffer();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, pface);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, faceArray, gl.STATIC_DRAW);

    const fbuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, fbuf);
    gl.bufferData(gl.ARRAY_BUFFER, FACECOORDS, gl.STATIC_DRAW);

    const ftex = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, ftex);
    gl.bufferData(gl.ARRAY_BUFFER, TEXCOORDS, gl.STATIC_DRAW);

    gl.useProgram(wedgeprog);

    const pers = mat4.create();
    mat4.perspective(pers, Math.PI / 8, gl.canvas.width / gl.canvas.height, 0.1, 100);

    const cameraVector = new Float32Array([0, 0, -4]);
    const viewMat = mat4.create();
    mat4.translate(viewMat, viewMat, cameraVector);

    index = {
      config: {
        faceWedge: response[0].faces.length * 1,
        faceParticle: response[1].faces.length * 1,
        faceFrame: 4
      },
      progs: {
        wedge: wedgeprog,
        particle: particleprog,
        frame: frameprog
      },
      buffers: {
        wedge: {
          vertex: buf,
          normal: norm,
          wedge: wNorm,
          face: el
        },
        particle: {
          vertex: pbuf,
          normal: pnorm,
          face: pface
        },
        face: {
          vertex: fbuf,
          texcoord: ftex
        }
      },
      textures: {
        framebuffer: fb,
        fbtexture: fbtex,
        fbdepth: fbdepth
      },
      matrices: {
        proj: pers,
        view: viewMat,
      },
      constants: {
        ambient: 0.2,
        cameraPosition: cameraVector,
      },
      lights: {
        worldPosition: new Float32Array(lightPos),
        color: new Float32Array([1, 1, 1]),
        intensity: 0.6
      },
      wedge: {
        aPosition: gl.getAttribLocation(wedgeprog, "aPosition"),
        aNormal: gl.getAttribLocation(wedgeprog, "aNormal"),
        aWedgeNormal: gl.getAttribLocation(wedgeprog, "aWedgeNormal"),

        uProjection: gl.getUniformLocation(wedgeprog, "projectionMatrix"),
        uView: gl.getUniformLocation(wedgeprog, "viewMatrix"),
        uModel: gl.getUniformLocation(wedgeprog, "modelMatrix"),
        uNormal: gl.getUniformLocation(wedgeprog, "normalMatrix"),
        uTime: gl.getUniformLocation(wedgeprog, "iTime"),
        uAmbient: gl.getUniformLocation(wedgeprog, "uAmbientStrength"),
        uCameraPosition: gl.getUniformLocation(wedgeprog, "uCameraPosition"),
        uGeometryColor: gl.getUniformLocation(wedgeprog, "uGeometryColor"),
        uAccent: gl.getUniformLocation(wedgeprog, "uAccent"),
        uBackground: gl.getUniformLocation(wedgeprog, "uBackground"),

        light: {
          worldPosition: gl.getUniformLocation(wedgeprog, "uLight.worldPosition"),
          color: gl.getUniformLocation(wedgeprog, "uLight.color"),
          intensity: gl.getUniformLocation(wedgeprog, "uLight.intensity")
        }
      },
      particle: {
        aPosition: gl.getAttribLocation(particleprog, "aPosition"),
        aNormal: gl.getAttribLocation(particleprog, "aNormal"),

        uProjection: gl.getUniformLocation(particleprog, "projectionMatrix"),
        uView: gl.getUniformLocation(particleprog, "viewMatrix"),
        uModel: gl.getUniformLocation(particleprog, "modelMatrix"),
        uNormal: gl.getUniformLocation(particleprog, "normalMatrix"),

        uAmbient: gl.getUniformLocation(particleprog, "uAmbientStrength"),
        uCameraPosition: gl.getUniformLocation(particleprog, "uCameraPosition"),
        uGeometryColor: gl.getUniformLocation(particleprog, "uGeometryColor"),

        light: {
          worldPosition: gl.getUniformLocation(particleprog, "uLight.worldPosition"),
          color: gl.getUniformLocation(particleprog, "uLight.color"),
          intensity: gl.getUniformLocation(particleprog, "uLight.intensity")
        }
      },

      frame: {
        aPosition: gl.getAttribLocation(frameprog, "aPosition"),
        aTexCoord: gl.getAttribLocation(frameprog, "aTexCoord"),

        uBuffer: gl.getUniformLocation(frameprog, "uBuffer"),
        uTime: gl.getUniformLocation(frameprog, "iTime"),
        uRes: gl.getUniformLocation(frameprog, "resolution")
      }
    };

    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.vertexAttribPointer(index.wedge.aPosition, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(index.wedge.aPosition);

    gl.bindBuffer(gl.ARRAY_BUFFER, norm);
    gl.vertexAttribPointer(index.wedge.aNormal, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(index.wedge.aNormal);

    gl.bindBuffer(gl.ARRAY_BUFFER, wNorm);
    gl.vertexAttribPointer(index.wedge.aWedgeNormal, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(index.wedge.aWedgeNormal);

    gl.uniformMatrix4fv(index.wedge.uProjection, false, pers);
    gl.uniformMatrix4fv(index.wedge.uView, false, viewMat);

    const mod = mat4.create();
    mat4.translate(mod, mod, SPHERE_PRIMARY);
    mat4.rotate(mod, mod, time * 0.2, [0.707, 0, 0]);
    mat4.rotate(mod, mod, time * -0.141, [0, 0, 0.707]);
    gl.uniformMatrix4fv(index.wedge.uModel, false, mod);

    const normMat = mat4.create();
    mat4.invert(normMat, mod);
    mat4.transpose(normMat, normMat);

    gl.uniformMatrix4fv(index.wedge.uNormal, false, normMat);
    gl.uniform1f(index.wedge.uTime, time);

    gl.uniform1f(index.wedge.uAmbient, index.constants.ambient); // total magic number
    gl.uniform3fv(index.wedge.uCameraPosition, cameraVector);
    gl.uniform3fv(index.wedge.uGeometryColor, GREEN);

    gl.uniform3fv(index.wedge.light.worldPosition, index.lights.worldPosition);
    gl.uniform3fv(index.wedge.light.color, index.lights.color);
    gl.uniform1f(index.wedge.light.intensity, index.lights.intensity);

    gl.uniform3fv(index.wedge.uAccent, accentColor);
    gl.uniform3fv(index.wedge.uBackground, backgroundColor);

    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, el);

    resizeCanvas(gl);
    window.addEventListener("resize", () => resizeCanvas(gl));

    p1 = performance.now();
    requestAnimationFrame(() => drawLoop(gl));
  }

  function drawLoop(gl) {
    let p2 = performance.now();
    deltaTime = p2 - p1;
    framePast.push(deltaTime);
    if (framePast.length > 60) {
      framePast.shift();
    }

    p1 = p2;

    // let timer = framePast.reduce((acc, cur) => acc + cur, 0);

    gl.useProgram(index.progs.wedge);

    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

    gl.bindBuffer(gl.ARRAY_BUFFER, index.buffers.wedge.vertex);
    gl.vertexAttribPointer(index.wedge.aPosition, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(index.wedge.aPosition);

    gl.bindBuffer(gl.ARRAY_BUFFER, index.buffers.wedge.normal);
    gl.vertexAttribPointer(index.wedge.aNormal, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(index.wedge.aNormal);

    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, index.buffers.wedge.face);

    const mod = mat4.create();
    mat4.translate(mod, mod, SPHERE_PRIMARY);
    mat4.rotate(mod, mod, time * 0.08, [0.707, 0, 0]);
    mat4.rotate(mod, mod, time * -0.06, [0, 0, 0.707]);

    const normMat = mat4.create();
    mat4.invert(normMat, mod);
    mat4.transpose(normMat, normMat);

    gl.uniformMatrix4fv(index.wedge.uModel, false, mod);
    gl.uniformMatrix4fv(index.wedge.uNormal, false, normMat);
    gl.uniformMatrix4fv(index.wedge.uProjection, false, index.matrices.proj);
    gl.uniform1f(index.wedge.uTime, (time += (deltaTime / 1000)) * 0.25);

    gl.uniform1f(index.wedge.uAmbient, 0.2); // total magic number
    gl.uniform3fv(index.wedge.uCameraPosition, index.constants.cameraPosition);
    gl.uniform3f(index.wedge.uGeometryColor, 0.625, 1, 0.6875);

    gl.uniform3fv(index.wedge.light.worldPosition, index.lights.worldPosition);
    gl.uniform3fv(index.wedge.light.color, index.lights.color);
    gl.uniform1f(index.wedge.light.intensity, index.lights.intensity);

    gl.uniform3fv(index.wedge.uAccent, accentColor);
    gl.uniform3fv(index.wedge.uBackground, backgroundColor);

    gl.bindFramebuffer(gl.FRAMEBUFFER, index.textures.framebuffer);
    // resize viewport texture when changing size
    gl.clear(gl.DEPTH_BUFFER_BIT | gl.COLOR_BUFFER_BIT);
    gl.viewport(0, 0, gl.canvas.width, gl.canvas.height);

    gl.drawElements(gl.TRIANGLES, index.config.faceWedge, gl.UNSIGNED_SHORT, 0);
    drawParticle(gl);
    drawBuffer(gl);
    requestAnimationFrame(() => drawLoop(gl));

  }

  function drawParticle(gl) {
    gl.useProgram(index.progs.particle);

    gl.bindBuffer(gl.ARRAY_BUFFER, index.buffers.particle.vertex);
    gl.vertexAttribPointer(index.particle.aPosition, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(index.particle.aPosition);

    gl.bindBuffer(gl.ARRAY_BUFFER, index.buffers.particle.normal);
    gl.vertexAttribPointer(index.particle.aNormal, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(index.particle.aNormal);

    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, index.buffers.particle.face);

    gl.uniformMatrix4fv(index.particle.uProjection, false, index.matrices.proj);
    gl.uniformMatrix4fv(index.particle.uView, false, index.matrices.view);

    gl.uniform3fv(index.particle.uGeometryColor, accentColor);


    gl.uniform1f(index.particle.uAmbient, index.constants.ambient);
    gl.uniform3fv(index.particle.uCameraPosition, index.constants.cameraPosition);
    gl.uniform3fv(index.particle.light.worldPosition, index.lights.worldPosition);
    gl.uniform3fv(index.particle.light.color, index.lights.color);
    gl.uniform1f(index.particle.light.intensity, index.lights.intensity);

    for (let i = 0; i < particleList.length; i++) {
      const particle = particleList[i];
      const partM = mat4.create();
      mat4.translate(partM, partM, particle.getPosition(time));
      mat4.scale(partM, partM, [0.04, 0.04, 0.04]);

      const partN = mat4.create();

      gl.uniformMatrix4fv(index.particle.uModel, false, partM);
      gl.uniformMatrix4fv(index.particle.uNormal, false, partN);
      gl.drawElements(gl.TRIANGLES, index.config.faceParticle, gl.UNSIGNED_SHORT, 0);
    }
  }

  function drawBuffer(gl) {
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);

    gl.useProgram(index.progs.frame);

    gl.activeTexture(gl.TEXTURE0);  // default but declaring for clarity :)

    gl.bindBuffer(gl.ARRAY_BUFFER, index.buffers.face.vertex);
    gl.vertexAttribPointer(index.frame.aPosition, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(index.frame.aPosition);

    gl.bindBuffer(gl.ARRAY_BUFFER, index.buffers.face.texcoord);
    gl.vertexAttribPointer(index.frame.aTexCoord, 2, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(index.frame.aTexCoord);

    gl.bindTexture(gl.TEXTURE_2D, index.textures.fbtexture);

    gl.uniform1i(index.frame.uBuffer, 0);

    gl.uniform1f(index.frame.uTime, time);

    gl.uniform2f(index.frame.uRes, gl.canvas.width, gl.canvas.height);

    gl.drawArrays(gl.TRIANGLE_FAN, 0, 4);
  }

  function compileProgram(gl, vert, frag) {
    const vertShader = compileShader(gl, gl.VERTEX_SHADER, vert);
    const fragShader = compileShader(gl, gl.FRAGMENT_SHADER, frag);

    const prog = gl.createProgram();
    gl.attachShader(prog, vertShader);
    gl.attachShader(prog, fragShader);
    gl.linkProgram(prog);

    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      console.error(gl.getProgramInfoLog(prog));
      gl.deleteProgram(prog);
      throw "Failed to link shader.";
    }

    return prog;
  }

  function compileShader(gl, type, text) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, text);
    gl.compileShader(shader);

    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      console.error(gl.getShaderInfoLog(shader));
      gl.deleteShader(shader);
      throw "Failed to compile " + (type === gl.VERTEX_SHADER ? "vertex" : "fragment") + " shader.";
    }
    return shader;
  }

  function Particle(x, y, z, velocity) {
    this.x = x;
    this.y = y;
    this.z = z;
    this.phase = Math.random() * 2 * Math.PI;
    if (typeof(velocity) == "object" && velocity.length == 3) {
      this.velocity = velocity;
    } else {
      velocity = [0, 0, 0];
    }
  }

  /*
  For reference: ES2015 class structure
  class Particle {
      constructor(x, y, z, velocity) {
          this.x = x;
          this.y = y;
          this.z = z;
          this.phase = Math.random() * 2 * Math.PI;
          if (typeof (velocity) == "object" && velocity.length == 3) {
              this.velocity = velocity;
          }
          else {
              velocity = [0, 0, 0];
          }
      }
      getPosition(tim) {
          return [this.x, this.y + Math.cos(tim / 5 + this.phase) * 0.15, this.z];
      }
  }
  */

  Particle.prototype.getPosition = function(tim) {
    return [this.x, this.y + Math.cos(tim / 5 + this.phase) * 0.15, this.z];
  };

  const FALLOFF = {
    INVERSE: (x, str = 1, pow = 2) => str / Math.pow(x, pow),
    LINEAR: (x, min = 0, max = 1) => (x < min ? 0 : (x > max ? 1 : (max - x) / (max - min)))
  };

  /**
  * Generates a simple spherical repulsion field.
  * Strength is 0 at maxRadius, <strength> at min radius, increasing exponentially inwards.
  */
  function SphereField(position, strength) {
    this.position = position;
    this.strength = strength;
    this.falloff = (x) => FALLOFF.INVERSE.apply(null, x);  // use defaults
  }

  /**
  * Sets the falloff function of a given field. Arguments field is contextual and based on the falloff function.
  * @param {FALLOFF} type - one of the available falloff functions:
  *   - INVERSE:
  *       @param {Number} str - The strength of the field.
  *       @param {Number} pow - Denominator is (distance)^(pow). Affects falloff curve with distance.
  *   - LINEAR:
          @param {Number} min - Minimum distance for falloff. Strength is 1 within min.
          @param {Number} max - Maximum distance for falloff. Strength is 0 out of max.
  */
  SphereField.prototype.setFalloff = function(type, ...args) {
    this.falloff = (x) => type.apply(null, [x, ...args]);
  };

  function id(q) {
    return document.getElementById(q);
  }
})();
