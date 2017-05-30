/**
 * HTML5 Drag and Drop uploader
 *
 * This file has been adapted for the needs of pagures from the work done by
 * Noah Petherbridge in https://github.com/kirsle/flask-multi-upload/
 * (released under public domain).
 *
 */

function doUpload(csrf_token, files) {
  $("#progress").show();
  var $progressBar   = $("#progress-bar");

  // Gray out the form.
  //$("#upload-form :input").attr("disabled", "disabled");

  // Initialize the progress bar.
  $progressBar.css({"width": "0%"});
  var fd = new FormData();
  fd.append('csrf_token', csrf_token);

  // Attach the files.
  for (var i = 0, ie = files.length; i < ie; i++) {
    // Collect the other form data.
    fd.append("filestream", files[i]);
  }

  var xhr = $.ajax({
    xhr: function() {
      var xhrobj = $.ajaxSettings.xhr();
      if (xhrobj.upload) {
        xhrobj.upload.addEventListener("progress", function(event) {
          var percent = 0;
          var position = event.loaded || event.position;
          var total    = event.total;
          if (event.lengthComputable) {
            percent = Math.ceil(position / total * 100);
          }

          // Set the progress bar.
          if (percent > 2){
            $progressBar.css({"color": "white"});
          }
          $progressBar.css({"width": percent + "%"});
          $progressBar.text(percent + "%");
        }, false)
      }
      return xhrobj;
    },
    url: UPLOAD_URL,
    method: "POST",
    contentType: false,
    processData: false,
    cache: false,
    data: fd,
    success: function(data) {
      $progressBar.css({"width": "100%", "color": "white"});

      // How'd it go?
      if (data.output === "notok") {
        // Uh-oh.
        window.alert(data);
        return;
      }
      else {
        var _txt = $("#comment").val();
        if (_txt) {
          _txt += '\n';
        }
        var _urls = '';
        for (var i = 0, ie = data.filenames.length; i < ie; i++) {
          _urls += '[![' + data.filenames[i] + ']('
            + data.filelocations[i] + ')]('
            + data.filelocations[i] + ')'
        }
        $("#comment").val(_txt + _urls)
      }
      setTimeout(
        function(){
          $("#progress").hide()
        },
        1000  /* 1 000ms = 2 s */
      );
    },
    error: function(data) {
      $("#progress").hide();
      var text = data.responseText;
      if ( !text || text === "" ) {
        text = '<p> An error occured when uploading your file. Could it be '
          + 'that it exceeds the maximum limit allowed? </p>'
          + '<p>Please contact an admin if this problem persist or is '
          + 'blocking you. Thanks! </p>';
      }
      var _elt = $('<div title="Error">' + text + '</div>');
      _elt.dialog({
        height: 'auto',
        width: '50%',
        modal: true,
        cache: false,
        close: function() {
            $(this).html("");
        },
      });
    }
  });
}

function initDropbox(csrf_token, id, upload) {
  if(typeof upload === 'undefined'){
    upload = true;
  }
  var $dropbox = $(id);

  // On drag enter...
  $dropbox.on("dragenter", function(e) {
    console.log('dragenter');
    e.stopPropagation();
    e.preventDefault();
    $(this).addClass("active");
  });

  // On drag over...
  $dropbox.on("dragover", function(e) {
    console.log('dragover');
    e.stopPropagation();
    e.preventDefault();
  });

  // On drop...
  $dropbox.on("drop", function(e) {
    console.log('drop');
    e.preventDefault();
    $(this).removeClass("active");

    // Get the files.
    var files = e.originalEvent.dataTransfer.files;

    if (upload == true) {
        doUpload(csrf_token, files);
    };
});

  // If the files are dropped outside of the drop zone, the browser will
  // redirect to show the files in the window. To avoid that we can prevent
  // the 'drop' event on the document.
  function stopDefault(e) {
    e.stopPropagation();
    e.preventDefault();
  }
  $(document).on("dragenter", stopDefault);
  $(document).on("dragover", stopDefault);
  $(document).on("drop", stopDefault);
}
