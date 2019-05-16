/* global mat4 */

/* i created this (please do not steal it i ask you nicely) */


(function() {
  let arrayWorker;  // our Ico Sphere generation worker.
  let time = 0;
  let p1;
  let deltaTime;
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
      throw "Error: Your browser doesn't support web workers. What the hell are you doing?";
    }
    arrayWorker = new Worker("icosphere.js");
    arrayWorker.onmessage = function(e) {
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

  function glSetup(response) {
    console.log(response[0]);
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

    let vertexArray = new Float32Array(response[0].vertices);
    let faceArray = new Uint16Array(response[0].faces);
    let normalArray = new Float32Array(response[0].normals);
    let wedgeNormal = new Float32Array(response[0].wedgeNormal);
    const wedgeprog = compileProgram(gl, id("vertex-wedge").innerText, id("fragment-wedge").innerText);
    const particleprog = compileProgram(gl, id("vertex-particle").innerText, id("fragment-particle").innerText);

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
    gl.bindBuffer(gl.ARRAY_BUFFER, pface);
    gl.bufferData(gl.ARRAY_BUFFER, faceArray, gl.STATIC_DRAW);

    gl.useProgram(wedgeprog);

    const index = {
      config: {
        faceCount: response[0].faces.length * 1
      },
      progs: {
        wedge: wedgeprog,
        particle: particleprog
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
        }
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
        uAmbient: gl.getUniformLocation(wedgeprog, "uAmbientStrength"),  // assuming white
        uCameraPosition: gl.getUniformLocation(wedgeprog, "uCameraPosition"),
        uGeometryColor: gl.getUniformLocation(wedgeprog, "uGeometryColor"),

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
      }
    }

    console.log(index.particle.aPosition);
    console.log(index.wedge.aPosition);

    // will need to bind, unbind, rebind vertices as necessary
    // good time to figure it out :)

    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.vertexAttribPointer(index.wedge.aPosition, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(index.wedge.aPosition);

    gl.bindBuffer(gl.ARRAY_BUFFER, norm);
    gl.vertexAttribPointer(index.wedge.aNormal, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(index.wedge.aNormal);

    gl.bindBuffer(gl.ARRAY_BUFFER, wNorm);
    gl.vertexAttribPointer(index.wedge.aWedgeNormal, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(index.wedge.aWedgeNormal);

    const pers = mat4.create();
    mat4.perspective(pers, Math.PI / 16, 16 / 9, 0.1, 100);
    gl.uniformMatrix4fv(index.wedge.uProjection, false, pers);

    const cameraVector = new Float32Array([0, 0, -15]);
    const viewMat = mat4.create();
    mat4.translate(viewMat, viewMat, cameraVector);
    gl.uniformMatrix4fv(index.wedge.uView, false, viewMat);

    // optimize
    const mod = mat4.create();
    mat4.rotate(mod, mod, (time) * 0.5, [0, 1, 0]);
    gl.uniformMatrix4fv(index.wedge.uModel, false, mod);

    const normMat = mat4.create();
    mat4.invert(normMat, mod);
    mat4.transpose(normMat, normMat);
    gl.uniformMatrix4fv(index.wedge.uNormal, false, normMat);
    gl.uniform1f(index.wedge.uTime, time);

    gl.uniform1f(index.wedge.uAmbient, 0.2); // total magic number
    gl.uniform3fv(index.wedge.uCameraPosition, cameraVector);
    gl.uniform3f(index.wedge.uGeometryColor, 0.625, 1, 0.6875);

    gl.uniform3f(index.wedge.light.worldPosition, -2, 2, 4);
    gl.uniform3f(index.wedge.light.color, 1, 1, 1);
    gl.uniform1f(index.wedge.light.intensity, 0.4);
    // todo: light falloff

    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, el);

    gl.drawElements(gl.TRIANGLES, response[0].faces.length, gl.UNSIGNED_SHORT, 0);

    p1 = performance.now();
    requestAnimationFrame(() => drawLoop(gl, index));
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
  function drawLoop(gl, index) {
    let p2 = performance.now();
    deltaTime = p2 - p1;
    framePast.push(deltaTime);
    if (framePast.length > 60) {
      framePast.shift();
    }
    p1 = p2;

    let timer = framePast.reduce((acc, cur) => acc + cur, 0);
    document.querySelector("p span").innerText = "" + Math.floor(60 / (timer / 1000));
    // spits out frame times, which could be necessary

    gl.useProgram(index.progs.wedge);

    gl.bindBuffer(gl.ARRAY_BUFFER, index.buffers.wedge.vertex);
    gl.vertexAttribPointer(index.wedge.aPosition, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(index.wedge.aPosition);


    const mod = mat4.create();
    mat4.rotate(mod, mod, time * 0.2, [0.707, 0, 0]);
    mat4.rotate(mod, mod, time * -0.141, [0, 0, 0.707]);

    const normMat = mat4.create();
    mat4.invert(normMat, mod);
    mat4.transpose(normMat, normMat);

    gl.uniformMatrix4fv(index.wedge.uModel, false, mod);
    gl.uniformMatrix4fv(index.wedge.uNormal, false, normMat);
    gl.uniform1f(index.wedge.uTime, (time += (deltaTime / 1000)) * 1.56);

    gl.drawElements(gl.TRIANGLES, index.config.faceCount, gl.UNSIGNED_SHORT, 0);  // capped at 65536 verts
    drawParticle(gl, index);
    requestAnimationFrame(() => drawLoop(gl, index));

  }

  function drawParticle(gl, index) {
    gl.bindBuffer(gl.ARRAY_BUFFER, index.buffers.particle.vertex);
    gl.vertexAttribPointer(index.particle.aPosition, 3, gl.FLOAT, false, 0, 0);
    gl.enableVertexAttribArray(index.particle.aPosition);

    // multiple draw calls per frame will be handled properly
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

  // particle functions

  function Particle(x, y, z, velocity) {
    this.x = x;
    this.y = y;
    this.z = z;
    if (typeof(velocity) == "object" && velocity.length == 3) {
      this.velocity = velocity;
    } else {
      velocity = [0, 0, 0];
    }
    // velocity
  }

  const FALLOFF = {
    INVERSE: (x, str = 1, pow = 2) => str / Math.pow(x, pow),
    LINEAR: (x, min = 0, max = 1) => (x < min ? 0 : x > max ? 1 : (max - x) / (max - min))
  }

  /**
  * Generates a simple spherical repulsion field.
  * Strength is 0 at maxRadius, <strength> at min radius, increasing exponentially inwards.
  */
  function SphereField(position, strength) {
    this.position = position;
    this.strength = strength;
    this.falloff = (x) => FALLOFF.INVERSE.apply(x);  // use defaults
  }

  /**
  * Sets the falloff function of a given field.
  */
  SphereField.prototype.setFalloff = function(type, ...args) {  // args are contextual
    this.falloff = (x) => type.apply([x, ...args])
  }



  function id(q) {
    return document.getElementById(q);
  }
})();
