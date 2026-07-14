# Guia: migrando para Power Automate Desktop (opcional)

Este guia traduz a lógica já validada em `automacao_core.py` para ações do
Power Automate Desktop. Não é necessário fazer essa migração — a versão em
Python/GUI já funciona e não depende de licenciamento extra. Use este guia
quando quiserem uma versão mais "corporativa", integrada ao 365, mantida
pela equipe sem depender de conhecimento em Python.

## Atenção — mesma limitação de login vale aqui

A tela de login do Hinova exige Código de autenticação (2FA) e um
reCAPTCHA (o Código cliente também aparece, mas é fixo por link — o
endereço de login já identifica a conta, então esse campo é preenchido
automaticamente pelo Hinova, sem precisar de nenhuma ação). Isso não é uma particularidade do script em Python —
**nenhuma ferramenta de automação, incluindo Power Automate Desktop, deve
tentar resolver o captcha programaticamente**. O fluxo no Power Automate
precisa do mesmo modelo híbrido: tentar preencher usuário/senha, e se o
captcha/2FA ainda aparecer, pausar o fluxo (ação "Esperar clique do mouse"
ou um diálogo pedindo confirmação) para a pessoa completar manualmente
antes de seguir com o restante automatizado.

## Quando a licença Premium é realmente necessária

- **Rodar o fluxo manualmente** (uma pessoa clica em "Executar" no Power
  Automate Desktop, com a máquina desbloqueada, e eventualmente completa o
  login): geralmente **não** exige licença Premium — entra no uso padrão
  do 365/Power Automate.
- **Disparo automático via Cloud Flow** (ex: iniciar o fluxo de desktop
  automaticamente quando a diretoria posta o % num canal do Teams) ou
  **execução desacompanhada** (unattended, sem ninguém logado na máquina):
  isso **exige** licença Premium — mas também exige que o login não
  dependa de captcha/2FA manual, já que não haveria ninguém para completar
  esse passo. Ou seja: automação 100% desacompanhada só é viável se o
  reCAPTCHA/2FA puderem ficar desativados de forma permanente para essa
  conta/IP, o que é uma decisão de quem administra o Hinova, com os riscos
  de segurança que isso implica.

Recomendação: comecem no modo "attended" (manual, sem gastar a licença) e
reservem a Premium para o dia em que quiserem automação ponta a ponta
(Teams → sistema, sem ninguém clicando em nada) — e só depois de avaliar
com segurança da informação se desativar captcha/2FA permanentemente é
aceitável para essa conta.

## Passo a passo

1. **Instalar/abrir o Power Automate Desktop** (já vem com o Windows 10/11,
   ou disponível na Microsoft Store) e logar com a conta corporativa 365.
2. Criar um novo **Fluxo de Desktop** (não um Cloud Flow) chamado, por
   exemplo, "Atualização de Cotas — Hinova".
3. **Parâmetros de entrada do fluxo**: criar duas entradas de arquivo
   (`CaminhoPT1`, `CaminhoPT2`) — isso equivale às caixas de seleção de
   arquivo da interface em Python, permitindo escolher a planilha na hora
   de rodar.
4. **Login no Hinova**:
   - Ação "Iniciar novo Chrome" apontando para a URL de login
     (`https://saturno.hinova.com.br/sga/sgav4_grupo_golplus/v5/login.php`).
   - Ação "Preencher campo de texto na página da web" para usuário e senha
     (guardados como entrada sensível do fluxo ou via Azure Key Vault).
   - Ação "Clicar em elemento da página da web" no botão "Entrar".
   - Ação de verificação (loop com "Aguardar" + "Obter detalhes de elemento
     da página da web") checando se a página de listagem de cotas carregou.
     Se não carregar em alguns segundos, mostrar uma caixa de diálogo
     pedindo para a pessoa completar o login manualmente (usuário, senha,
     código de autenticação, captcha — o código cliente já vem preenchido)
     e clicar em "OK" para o fluxo continuar — igual ao que `aguardar_login_manual` faz no Python.
5. **Para cada planilha (PT1, depois PT2)**:
   - Ação "Iniciar Excel" / "Ler dados de uma planilha do Excel" para
     carregar as colunas Código, Tipo do veículo e Valor.
   - Ação "Para cada linha" da tabela lida.
   - Dentro do loop:
     - Preencher o campo `codigo_cota` com o código da linha.
     - Tentar preencher `descricao_cota`; usar um bloco
       **"Ao ocorrer erro" → tentar novamente com outra ação** apontando
       para `tipo_veiculo_cota` caso o primeiro campo não exista na tela
       (isso reproduz o fallback que o script Python já faz).
     - Clicar no menu de ações da linha de resultado e no botão de editar.
     - Preencher `cota_valor` com o novo valor (2 casas decimais).
     - Clicar em salvar.
     - Ação "Escrever célula do Excel" numa planilha de histórico separada,
       registrando código, valor antigo e novo valor — igual ao
       `historico_atualizacoes.xlsx` gerado hoje.
     - Em caso de erro em qualquer ação do loop, capturar com
       "Ao ocorrer erro" e gravar a linha numa planilha de "itens com erro",
       sem interromper o fluxo.
   - Fora do loop: voltar para a página de listagem de cotas antes da
     próxima iteração (equivalente ao `driver.get(COTAS_URL)` do script).
6. Ao final do fluxo: fechar o navegador e salvar as planilhas de histórico
   e erros com data/hora no nome (ação "Obter data/hora atual" + concatenar
   no nome do arquivo).
7. **Publicar e compartilhar** o fluxo de desktop com o grupo de colegas que
   vão executá-lo, ou deixá-lo salvo numa máquina compartilhada. A execução
   passa a ser: abrir o Power Automate Desktop → selecionar o fluxo →
   "Executar" → escolher os arquivos PT1/PT2 → completar o login se pedido.

## Recomendação de transição

Não é preciso migrar tudo de uma vez. Sugestão:
1. Usar a versão em Python (GUI) já entregue durante as férias.
2. Quando houver tempo, montar o fluxo no Power Automate Desktop seguindo
   este guia, testando com um lote pequeno de cotas antes de confiar nele
   para o volume total.
3. Rodar as duas versões em paralelo por um ciclo de reajuste, comparando
   os resultados (planilha de histórico de uma vs. da outra).
4. Só então aposentar a versão em Python, se o Power Automate se mostrar
   igual ou mais confiável.
