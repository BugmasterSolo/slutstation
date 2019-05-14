/* global mat4 */

/* i created this (please do not steal it i ask you nicely) */


(function() {
  let arrayWorker;  // our Ico Sphere generation worker.
  let time = 0;
  let p1;
  let framePast = new Array(60);
  for (let i = 0; i < 60; i++) {
    framePast[i] = 1000;
  }

  window.addEventListener("load", init);

  /**
  * Creates the icosphere web worker and passes relevant info to it, before sending the result to the glSetup function.
  */
  function init() {
    // create a new worker and get it to generate our page data. wait on the thread while it does so.
    if (!(typeof(Worker) == "function")) {
      throw "Error: Your browser doesn't support web workers. What the hell are you doing dude? Like everything supports them!";
    }
    arrayWorker = new Worker("icosphere.js");
    arrayWorker.onmessage = function(e) {
      glSetup(e.data);
    };
    arrayWorker.postMessage("4");
  }

  function glSetup(response) {
    gl = document.getElementById("primary-canvas").getContext("webgl");

    let ext = gl.getExtension("WEBGL_debug_renderer_info");
    if (ext) {
      console.log(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL));
      console.log(gl.getParameter(ext.UNMASKED_VENDOR_WEBGL));
    }

    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);

    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

    let vertexArray = new Float32Array(response.vertices);
    let faceArray = new Uint16Array(response.faces);
    let normalArray = new Float32Array(response.normals);
    let wedgeNormal = new Float32Array(response.wedgeNormal);
    const prog = compileProgram(gl, id("vertex-print").innerText, id("fragment-print").innerText);

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

    gl.useProgram(prog);

    const index = {
      config: {
        // add more as necessary
        faceCount: faceArray.length * 1
      },

      aPosition: gl.getAttribLocation(prog, "aPosition"),
      aNormal: gl.getAttribLocation(prog, "aNormal"),
      aWedgeNormal: gl.getAttribLocation(prog, "aWedgeNormal"),

      uProjection: gl.getUniformLocation(prog, "projectionMatrix"),
      uView: gl.getUniformLocation(prog, "viewMatrix"),
      uModel: gl.getUniformLocation(prog, "modelMatrix"),
      uNormal: gl.getUniformLocation(prog, "normalMatrix"),
      uTime: gl.getUniformLocation(prog, "iTime"),
      uAmbient: gl.getUniformLocation(prog, "uAmbientStrength"),  // assuming white
      uCameraPosition: gl.getUniformLocation(prog, "uCameraPosition"),
      uGeometryColor: gl.getUniformLocation(prog, "uGeometryColor"),
      // single light for now
      light: {
        worldPosition: gl.getUniformLocation(prog, "uLight.worldPosition"),
        color: gl.getUniformLocation(prog, "uLight.color"),
        intensity: gl.getUniformLocation(prog, "uLight.intensity")
      }
    }

    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.vertexAttribPointer(index.aPosition, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(index.aPosition);

    gl.bindBuffer(gl.ARRAY_BUFFER, norm);
    gl.vertexAttribPointer(index.aNormal, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(index.aNormal);

    gl.bindBuffer(gl.ARRAY_BUFFER, wNorm);
    gl.vertexAttribPointer(index.aWedgeNormal, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(index.aWedgeNormal);

    const pers = mat4.create();
    mat4.perspective(pers, Math.PI / 16, 16 / 9, 0.1, 100);
    gl.uniformMatrix4fv(index.uProjection, false, pers);

    const cameraVector = new Float32Array([0, 0, -15]);
    const viewMat = mat4.create();
    mat4.translate(viewMat, viewMat, cameraVector);
    gl.uniformMatrix4fv(index.uView, false, viewMat);

    // optimize
    const mod = mat4.create();
    mat4.rotate(mod, mod, (time += 0.01), [0, 1, 0]);
    gl.uniformMatrix4fv(index.uModel, false, mod);

    const normMat = mat4.create();
    mat4.invert(normMat, mod);
    mat4.transpose(normMat, normMat);
    gl.uniformMatrix4fv(index.uNormal, false, normMat);
    gl.uniform1f(index.uTime, time);

    gl.uniform1f(index.uAmbient, 0.2); // total magic number
    gl.uniform3fv(index.uCameraPosition, cameraVector);
    gl.uniform3f(index.uGeometryColor, 0.625, 1, 0.6875);

    gl.uniform3f(index.light.worldPosition, -2, 2, 4);
    gl.uniform3f(index.light.color, 1, 1, 1);
    gl.uniform1f(index.light.intensity, 0.4);
    // todo: light falloff

    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, el);

    p1 = performance.now();
    gl.drawElements(gl.TRIANGLES, response.faces.length, gl.UNSIGNED_SHORT, 0);
    requestAnimationFrame(() => drawLoop(gl, prog, index));
  }

  /* todo: render to frame buffer and add postFX
  * framebuffer should allow for optimization on lower hardware, just by scaling it down
  * account for less powerful hardware w performance analytics (time per frame, from last)
  * like uh figure out how to get gpu info on the fly and roll w it

  * what i would love for animation:
  *   - rotation appears random.
  *   - about once a second, extrudes update w lerp animation. calc perlin twice and interpolate between (expensive?)
  *   - colors should do the same, but instantly.
  *   - background: low resolution plain icospheres floating about as particles.
  *       - take some cues on interface design and give it some flair and personality.
  *         (that means looking at reference material!!!)
  */
  function drawLoop(gl, prog, index) {
    let p2 = performance.now();
    framePast.push(p2 - p1);
    if (framePast.length > 60) {
      framePast.shift();
    }
    let timer = framePast.reduce((acc, cur) => acc + cur, 0);
    document.querySelector("p span").innerText = "" + Math.floor(60 / (timer / 1000));
    p1 = p2;
    // spits out frame times, which could be necessary

    const mod = mat4.create();
    mat4.rotate(mod, mod, time, [0, 1, 0]);

    const normMat = mat4.create();
    mat4.invert(normMat, mod);
    mat4.transpose(normMat, normMat);

    gl.uniformMatrix4fv(index.uModel, false, mod);
    gl.uniformMatrix4fv(index.uNormal, false, normMat);
    gl.uniform1f(index.uTime, time += 0.01);


    gl.drawElements(gl.TRIANGLES, index.config.faceCount, gl.UNSIGNED_SHORT, 0);  // capped at 65536 verts
    requestAnimationFrame(() => drawLoop(gl, prog, index));
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
      throw "Failed to compile shader.";
    }
    return shader;
  }

  function id(q) {
    return document.getElementById(q);
  }
})();
