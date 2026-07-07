(function () {
  "use strict";

  var form = document.getElementById("form");
  var input = document.getElementById("url");
  var button = document.getElementById("submit");
  var statusEl = document.getElementById("status");

  var YT_RE = /^(https?:\/\/)?(www\.|m\.|music\.)?(youtube\.com|youtu\.be)\//i;

  function setStatus(message, kind) {
    statusEl.textContent = message;
    statusEl.className = "status" + (kind ? " " + kind : "");
  }

  function setBusy(busy) {
    button.disabled = busy;
    input.disabled = busy;
    button.textContent = busy ? "Working" : "Get MP3";
  }

  function filenameFromHeader(header) {
    if (!header) return null;
    var match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(header);
    return match ? decodeURIComponent(match[1]) : null;
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var url = input.value.trim();
    if (!YT_RE.test(url)) {
      setStatus("That doesn't look like a YouTube link.", "error");
      return;
    }

    setBusy(true);
    setStatus("Fetching and converting, this can take a bit.", "loading");

    fetch(window.BACKEND_URL + "/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url }),
    })
      .then(function (res) {
        if (!res.ok) {
          return res
            .json()
            .catch(function () {
              return { detail: "Request failed (" + res.status + ")." };
            })
            .then(function (data) {
              throw new Error(data.detail || data.error || "Request failed.");
            });
        }
        var name =
          filenameFromHeader(res.headers.get("Content-Disposition")) || "audio.mp3";
        return res.blob().then(function (blob) {
          return { blob: blob, name: name };
        });
      })
      .then(function (result) {
        var objectUrl = URL.createObjectURL(result.blob);
        var a = document.createElement("a");
        a.href = objectUrl;
        a.download = result.name;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(objectUrl);
        setStatus("Done. Check your downloads.", "ok");
      })
      .catch(function (err) {
        setStatus(err.message || "Something went wrong.", "error");
      })
      .finally(function () {
        setBusy(false);
      });
  });
})();
