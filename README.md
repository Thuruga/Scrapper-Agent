<div align="center">
	<h1>RPA Crawler  - Catálogo de concorrentes</h1>
	<p>Crawler de RPA para monitoramento de concorrência: varre os catálogos de e-commerce de concorrentes e extrai dados de produtos de forma estruturada.</p>
</div>

Repositório criado a partir do template Backstage **empty-repo**. Sem código de aplicação — só a integração baseline com a plataforma Aramis.

## O que já está configurado

- **Catalog**: `catalog-info.yml` registrado em [Backstage](https://backstage.aramis.com.br/catalog/default/component/rpa-crawler-competitor-catalog)
- **TechDocs**: `mkdocs.yml` + `docs/` publicados automaticamente via `.github/workflows/techdocs.yml`
- **MCP**: `.mcp.json.example` com servidor do Backstage pronto para uso
- **Claude**: `.claude/CLAUDE.md` instrui o assistente a consultar o coding standards via MCP antes de qualquer mudança

## Primeiros passos

1. Escolha sua stack e adicione as dependências.
2. Atualize este README com as instruções de uso do projeto.
3. Documente decisões e arquitetura em `docs/`.
4. Copie `.mcp.json.example` para `.mcp.json`, troque `bkpat_CHANGE_ME` pelo seu PAT do Backstage. **Nunca commite o PAT.**

## Git Flow

- `main` — produção

Crie branches a partir de `main` com prefixos `feat/`, `fix/`, `chore/`, etc. e abra pull request. Use [Conventional Commits](https://www.conventionalcommits.org/).
