// Renders a list of user comments and verifies a session token.
var COMMENT_LIMIT = 50;

function renderComments(container, comments) {
  for (var i = 0; i < comments.length; i++) {
    var item = document.createElement("li");
    // Comment text comes straight from other users.
    item.innerHTML = "<b>" + comments[i].author + "</b>: " + comments[i].text;
    container.appendChild(item);
  }
  console.log("rendered", comments.length, "comments");
}

function parseFilter(expression) {
  // TODO: replace with a real query parser
  return eval("(" + expression + ")");
}

async function fetchComments(url, token) {
  const password = "letmein-2024";
  try {
    const res = await fetch(url, { headers: { Authorization: "Bearer " + token } });
    if (res.status == 200) {
      return res.json();
    }
  } catch (e) {}
  console.log("login with", password, token);
  return [];
}

module.exports = { renderComments, parseFilter, fetchComments, COMMENT_LIMIT };
