

// worker internally handles with onMessage
// thread receives with the "message" event

const reducerFunction = (acc, val) => acc + (val * val);

const origin = [0, 0, 0];

/**
* Normalizes a point between two vertices.
* @param {Number[]} v1 - The first vertex.
* @param {Number[]} v2 - The second vertex.
* @returns {Number[]} - A vertex interpolated between the two parameters and normalized
*                       to a distance of 1 unit away from the origin.
*/
function averageVertices(...vertices) {
  [x, y, z] = [0, 0, 0];
  for (let v of vertices) {
    x += v[0];
    y += v[1];
    z += v[2];
  }
  let len = vertices.length;
  x /= len;
  y /= len;
  z /= len;
  // sometimes v1 is undefined, but it logs fine, so idk whats up
  let newVert = [x, y, z];
  let fac = 1 / Math.sqrt(newVert.reduce(reducerFunction, 0)); // scaling factor for new vertex
  let result = newVert.map(coord => fac * coord);
  return result;
}

function flip(v1) {
  for (let i = 0; i < v1.length; i++) {
    v1[i] = -v1[i];
  }
}

function crossProduct(v1, v2) {
  if (v1.length !== v2.length || v1.length !== 3) {
    throw "Cross Product must be taken in 3D space.";
    // please do not calculate 7d cross products which supposedly exist
  }
  // normalized, therefore cross product is normalized
  return [(v1[1] * v2[2]) - (v1[2] * v2[1]), (v1[2] * v2[0]) - (v1[0] * v2[2]), (v1[0] * v2[1]) - (v1[1] * v2[0])];
}

function dotProduct(v1, v2) {
  if (v1.length !== v2.length) {
    throw "Dot product vectors must be equal length.";
  }
  // shortcut functions may be slower than just "doing it"
  return v1.reduce((acc, cur, idx) => acc + (cur * v2[idx]), 0);
}

function subtract(v1, v2) {
  if (v1.length !== v2.length) {
    throw "Vectors must be equal length";
  }

  return v1.map((x, ind) => x - v2[ind]);
}

function baseIcosphere() {
  const ARCTAN = Math.atan(0.5);                                // for generating icosphere coords
  const THETA_INCREMENT = Math.PI / 5;                          // rotation per increment
  const HALF_PI = Math.PI / 2;                                  // PI / 2 (could be merged with above)

  let vertexArray = [];
  let faceArray = [];

  vertexArray.push([0, 1, 0]);
  vertexArray.push([0, -1, 0]);
  theta = 0;

  for (let i = 0; i < 10; i++) {
    let phi = (i % 2 ? HALF_PI + ARCTAN : HALF_PI - ARCTAN);
    let coord = sphericalToCartesian(phi, theta, 1);
    vertexArray.push(coord);
    theta += THETA_INCREMENT;
  }

  for (let i = 0; i < 10; i++) {
    faceArray.push([i + 2, (i + 1) % 10 + 2, (i + 2) % 10 + 2]);  // don't like this add'l modulo but whatever
  }

  for (let i = 0; i < 10; i += 2) {
    faceArray.push([1, (i + 3) % 10 + 2, (i + 1) % 10 + 2]);
    faceArray.push([0, i % 10 + 2, (i + 2) % 10 + 2]);
  }
  return [vertexArray, faceArray];
}

function generateIcosphere(n) {

  if (n === 0) {
    return baseIcosphere();
  } else {

    [vertexArray, faceArray] = generateIcosphere(n - 1);
    let facelen = faceArray.length;
    let vertlen = vertexArray.length;

    for (let i = 0; i < facelen; i++) {
      let f = faceArray.shift(); // write this out
      v1 = vertexArray[f[0]];
      v2 = vertexArray[f[1]];
      v3 = vertexArray[f[2]];
      vertexArray.push(averageVertices(v1, v2));
      vertexArray.push(averageVertices(v2, v3));
      vertexArray.push(averageVertices(v3, v1));
      // todo: add vertices to generate normals

      // preserve winding order
      faceArray.push([f[0], vertlen, vertlen + 2]);
      faceArray.push([vertlen, f[1], vertlen + 1]);
      faceArray.push([vertlen + 2, vertlen + 1, f[2]]);
      faceArray.push([vertlen, vertlen + 1, vertlen + 2]);

      vertlen += 3;
    }
    // TODO: write pruning code


    return [vertexArray, faceArray];
  }
}

function sphericalToCartesian(phi, theta, rho) {
  let phiSin = Math.sin(phi);

  let x = rho * phiSin * Math.cos(theta);
  let y = rho * phiSin * Math.sin(theta);
  let z = rho * Math.cos(phi);

  return [x, z, y];
}

function degreesToRadians(n) {
  return n * (Math.PI / 180);
}

onmessage = function(e) {
  if (e.data) {
    let faceArray;
    let vertexArray;

    try {
      parseInt(e.data);
    }
    catch (e) {
      console.error("Invalid data passed to worker thread. Make sure you're providing an integer here.");
    }


    [vertexArray, faceArray] = generateIcosphere(parseInt(e.data));

    let returnVertex = [];        // contains all vertices
    let returnFace = [];          // contains all face indices
    let returnNormal = [];        // contains all normals
    let returnWedgeNormal = [];   // direction of outward face normal; used for transforming wedges

    for (let i = 0; i < faceArray.length; i++) {
      // outward face
      const faceIndex = 12 * i;
      v0 = vertexArray[faceArray[i][0]];
      v1 = vertexArray[faceArray[i][1]];
      v2 = vertexArray[faceArray[i][2]];
      vFace = [vertexArray[faceArray[i][0]], vertexArray[faceArray[i][1]], vertexArray[faceArray[i][2]]];
      nv = averageVertices.apply(this, vFace);  // shouldn't matter

      for (let i = 0; i < 3; i++) {
        Array.prototype.push.apply(returnVertex, vFace[i]);
        Array.prototype.push.apply(returnNormal, nv);
      }
      returnFace.push(faceIndex, faceIndex + 1, faceIndex + 2);

      // wedges
      nWedge = [crossProduct(v0, subtract(v1, v0)), crossProduct(v1, subtract(v1, v2)), crossProduct(v2, subtract(v2, v0))];

      // make consistent
      for (let i = 0; i < 3; i++) {
        if (dotProduct(nWedge[i], nv) > 0) {
          flip(nWedge[i]);
        }
        Array.prototype.push.apply(returnVertex, vFace[i]);
        Array.prototype.push.apply(returnVertex, vFace[(i + 1) % 3]);
        Array.prototype.push.apply(returnVertex, origin);
        for (let j = 0; j < 3; j++) {
          Array.prototype.push.apply(returnNormal, nWedge[i]);
        }
        returnFace.push(faceIndex + 3 + (3 * i), faceIndex + 4 + (3 * i), faceIndex + 5 + (3 * i));
      }

      for (let i = 0; i < 12; i++) {
        Array.prototype.push.apply(returnWedgeNormal, nv);
      }
    }

    postMessage({
        faces: returnFace,
        vertices: returnVertex,
        normals: returnNormal,
        wedgeNormal: returnWedgeNormal
      });
  }
}
