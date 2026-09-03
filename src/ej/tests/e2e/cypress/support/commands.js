//Access Django admin painel to remove user.
Cypress.Commands.add('removesCypressUser', () => {
    cy.visit('/admin')
    cy.get('#id_username').type(Cypress.env('adminCredentials')['email'], {force: true})
    cy.get('#id_password').type(Cypress.env('adminCredentials')['password'], {force: true})
    cy.get('input[type="submit"]').click({force: true})
    cy.get('th[scope="row"] a[href="/admin/ej_users/user/"]').click({force: true})
    cy.get('#changelist-search input[type="text"]').type(`${Cypress.env("userCredentiails")["email"]}{enter}`, {force: true})
    cy.get('p[class="paginator"]').then(($paginator) => {
      if ($paginator[0].textContent != '\n\n0 users\n\n\n') {
        cy.get('.action-checkbox input[type="checkbox"]').click({force: true})
        cy.get('select[name="action"]').select('delete_selected')
        cy.get('.actions button[type="submit"]').click({force: true})
        cy.get('input[type="submit"]').click({force: true})
      }
    })
  cy.get("#logout-form").submit()
})

Cypress.Commands.add('createConversation', () => {
    cy.get('a[title="Nova conversa"]').first().click()
    cy.get('.conversation-balloon h1').should('contain', 'Configurações básicas')
    cy.get('#id_text').type("O que você acha do avanço da inteligência artificial na sociedade moderna?")
    cy.get('input[name=tags]').type("IA,machine learning")
    cy.get('input[name=title]').type("avanços da IA e2e")
    cy.get('#id_anonymous_votes_limit').type(2)
    cy.get('textarea[name=comment-1]').type("Todos os humanos serão substituidos por máquinas")
    cy.get('textarea[name=comment-2]').type("É o capitalismo se reinventando mais uma vez")
    cy.get('textarea[name=comment-3]').type("O chat gpt mudou minha forma de trabalhar")
    cy.get('input[type=submit]').click()
})

Cypress.Commands.add('createCustomConversation', () => {
  cy.get('a[title="Nova conversa"]').first().click()
  cy.get('#id_text').type("O que você acha do financiamento das praças públicas?")
  cy.get('input[name=title]').type("praças públicas")
  cy.get('input[name=tags]').type("infraestrutura")
  cy.get('#id_anonymous_votes_limit').type(2)
  cy.get('.conversation-form__custom-richtext label').should('contain', 'Texto adicional a ser apresentado na tela de boas-vindas')
  cy.get('#id_ending_message').typeCkeditor("Muito obrigada pela participação, ela é muito importante.");
  cy.get('input[type=submit]').click()
})

//Access Django admin painel to remove conversation.
Cypress.Commands.add('removesCypressConversation', (conversation_title="avanços da IA e2e") => {
   cy.visit('/admin')
    cy.get('#id_username').type(Cypress.env('adminCredentials')['email'], {force: true})
    cy.get('#id_password').type(Cypress.env('adminCredentials')['password'], {force: true})
    cy.get('input[type="submit"]').click({force: true})
    cy.get('th[scope="row"] a[href="/admin/ej_conversations/conversation/"]').click({force: true})
    cy.get('a').contains('Hoje').click()
    cy.get('a').contains(conversation_title).then(($elements)=>{
      if ($elements.length > 0) {
        cy.get('a').contains(conversation_title).click({force: true})
        cy.get('a[class=deletelink]').click({force: true})
        cy.get('input[type="submit"]').click({force: true})
      }
    })
    cy.get("#logout-form").submit({force: true})
})

Cypress.Commands.add('removesBannerConversation', () => {
  cy.visit('/admin')
  cy.get('#id_username').type(Cypress.env('adminCredentials')['email'], {force: true})
  cy.get('#id_password').type(Cypress.env('adminCredentials')['password'], {force: true})
  cy.get('input[type="submit"]').click({force: true})
  cy.get('th[scope="row"] a[href="/admin/ej_conversations/conversation/"]').click({force: true})
  cy.get('a').contains("educacao e2e").then(($elements)=>{
    if ($elements.length > 0) {
      cy.get('a').contains("educacao e2e").click({force: true})
      cy.get('a[class=deletelink]').click({force: true})
      cy.get('input[type="submit"]').click({force: true})
    }
  })
  cy.get("#logout-form").submit({force: true})
})

//Register new user using EJ form
Cypress.Commands.add('registerUser', () => {
    cy.visit('/register')
    cy.get('input[name="name"]').type(`${Cypress.env("userCredentiails")["name"]}`)
    cy.get('input[name="email"]').type(`${Cypress.env("userCredentiails")["email"]}`)
    cy.get('input[name="password"]').type(`${Cypress.env("userCredentiails")["password"]}`)
    cy.get('input[name="password_confirm"]').type(`${Cypress.env("userCredentiails")["password"]}`)
    cy.get('#use-terms').check()
    cy.get('#privacy-terms').check()
    cy.get('input[type="submit"]').click()
})

Cypress.Commands.add('logout', () => {
  cy.visit("/")
  cy.get('a[onclick="logout()"]').click({force: true})
})

Cypress.Commands.add('login', () => {
    cy.visit('/login')
    cy.get('input[type="email"]').type(`${Cypress.env("userCredentiails")["email"]}{enter}`)
    cy.get('input[type="password"]').type(`${Cypress.env("userCredentiails")["password"]}{enter}`)
})

Cypress.Commands.add('typeCkeditor', {
  prevSubject: true,
}, (prevSubject, html) => {
  return cy.wrap(prevSubject).invoke('attr', 'id').then((id) => {
    return cy.window().should((window) => {
      expect(window.editors).to.have.property(id);
    }).then((window) => {
      window.editors[id].setData(html);
    });
  });
});
