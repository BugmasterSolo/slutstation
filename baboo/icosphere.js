
"use strict";
// worker internally handles with onMessage
// thread receives with the "message" event

const reducerFunction = (acc, val) => acc + (val * val);

const origin = [0, 0, 0];

/**
* Normalizes a point between two vertices.
* @param {...Number[3]} vertices - List of all passed vertices.
* @returns {Number[3]} - A vertex interpolated between the two parameters and normalized
*                       to a distance of 1 unit away from the origin.
*/
function averageVertices(...vertices) {
  let [x, y, z] = [0, 0, 0];
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

/**
* Flips all values of a given vertex. Useful in the event that a point is negatively scaled.
* @param {Number[]} v1 - Inputted n-dimensional vertex.
* @returns {Number[]} Flipped vertex.
*/
function flip(v1) {
  for (let i = 0; i < v1.length; i++) {
    v1[i] = -v1[i];
  }
}

/**
* Takes the cross product of two 3-dimensional arrays.
* @param {Number[]} v1 - The first input vector.
* @param {Number[]} v2 - The second input vector.
* @returns {Number[]} The cross product v1 x v2.
*/
function crossProduct(v1, v2) {
  if (v2.length !== 3 || v1.length !== 3) {
    throw "Cross Product must be taken in 3D space.";
    // please do not calculate 7d cross products which supposedly exist
  }
  // normalized, therefore cross product is normalized
  return [(v1[1] * v2[2]) - (v1[2] * v2[1]), (v1[2] * v2[0]) - (v1[0] * v2[2]), (v1[0] * v2[1]) - (v1[1] * v2[0])];
}

/**
* Takes the dot product of two n-dimensional arrays, provided they are the same length.
* @param {Number[]} v1 - The first input vector.
* @param {Number[]} v2 - The second input vector.
* @returns {Number} - The dot product v1 . v2.
*/
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
  let theta = 0;

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

    let [vertexArray, faceArray] = generateIcosphere(n - 1);
    let facelen = faceArray.length;
    let vertlen = vertexArray.length;

    for (let i = 0; i < facelen; i++) {
      let f = faceArray.shift(); // write this out
      let v1 = vertexArray[f[0]];
      let v2 = vertexArray[f[1]];
      let v3 = vertexArray[f[2]];
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

// deal with passing multiple pieces of data
// pass array pairs to onmessage, parse one by one, return array of polished geometry
onmessage = function(e) {
  if (e.data) {
    let faceArray;
    let vertexArray;
    let subdiv;
    let message = [];
    for (let n = 0; n < e.data.length; n++) {
      try {
        console.log(e.data[n].subdivisions);
        subdiv = parseInt(e.data[n].subdivisions);
      }
      catch (e) {
        console.error("Invalid data passed to worker thread. Make sure you're providing an integer here.");
      }


      [vertexArray, faceArray] = generateIcosphere(subdiv);

      let returnVertex = [];        // contains all vertices
      let returnFace = [];          // contains all face indices
      let returnNormal = [];        // contains all normals
      let returnWedgeNormal = [];   // direction of outward face normal; used for transforming wedges

      for (let i = 0; i < faceArray.length; i++) {
        // outward face
        const faceIndex = (e.data[n].wedge ? 12 : 3) * i;
        let v0 = vertexArray[faceArray[i][0]];
        let v1 = vertexArray[faceArray[i][1]];
        let v2 = vertexArray[faceArray[i][2]];
        let vFace = [vertexArray[faceArray[i][0]], vertexArray[faceArray[i][1]], vertexArray[faceArray[i][2]]];
        let nv = averageVertices.apply(this, vFace);  // shouldn't matter

        for (let i = 0; i < 3; i++) {
          Array.prototype.push.apply(returnVertex, vFace[i]);
          Array.prototype.push.apply(returnNormal, nv);
        }
        returnFace.push(faceIndex, faceIndex + 1, faceIndex + 2);

        if (e.data[n].wedge) {

          // wedges generated here. allow this to be skipped.
          // these are particles that can be drawn for cheap in an additional draw call.
          let nWedge = [crossProduct(v0, subtract(v1, v0)), crossProduct(v1, subtract(v1, v2)), crossProduct(v2, subtract(v2, v0))];

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
      }

      let temp = {
        faces: returnFace,
        vertices: returnVertex,
        normals: returnNormal,
        wedgeNormal: (e.data[n].wedge ? returnWedgeNormal : null)
      };

      message.push(temp);

    }
    postMessage(message);
  }
};
