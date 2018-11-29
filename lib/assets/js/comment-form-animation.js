function showForm(button) {
       var commentform = document.getElementById("commentform");
       buttonicon = button[0].firstElementChild
       if(commentform.classList.contains("show")){
            makeFormDisappear(commentform, buttonicon);
       }
       else{
            commentform.classList.add("show");
            buttonicon.className = buttonicon.className.replace("plus", "times")
       }
       $('#id_content').keyup(updateCharactersCount);
       $('#id_content').keydown(updateCharactersCount);
  }


$(document).click(function(event) {
  if(!$(event.target).closest('#commentform').length && !$(event.target).closest('#button-create').length) {
    var commentform = document.getElementById("commentform");
    if(commentform && commentform.classList.contains("show")) {
      button = document.getElementsByClassName('fas fa-times')[0];
      makeFormDisappear(commentform, button);
    }
  }
});

function updateCharactersCount() {
    var cs = $(this).val().length;
    $('#characters-count').text(cs + ' / 252');
}

function makeFormDisappear(form, button) {
  form.className = "hideanimation";
  setTimeout(function(){
      form.className = commentform.className.replace("hideanimation", "");
  }, 500);
  button.className = buttonicon.className.replace("times", "plus")

}
