import { H1, H2, H3, H4, H5, H6 } from "./Titles"
import { P } from "./Paragraphs"
import { Section } from "./Section"

export const Titles = () => (
  <>
    <H1>A big title</H1>
    <H2>Still a big title, but not so much</H2>
    <H3>A less pretentious title</H3>
    <H4>Quite an humble title</H4>
    <H5>Getting timid</H5>
    <H6>Or very discret</H6>
  </>
)

const HR = () => <hr style={{ margin: 0, padding: 0, border: "1px solid black" }} />

export const TitlesWithParagraphs = ({ withHr = false }) => (
  <>
    {withHr ? <HR /> : null}

    <Section>
      <H1>Eat at Joe's</H1>
      <P>So good you won't believe it's real.</P>
    </Section>

    {withHr ? <HR /> : null}

    <Section>
      <H2>Joe's special</H2>
      <P>It's a secret, but it's good.</P>
    </Section>

    {withHr ? <HR /> : null}

    <Section>
      <H3>Joe's special with cheese</H3>
      <P>It's a secret, but it's good. And it has cheese.</P>
      <P>And even a second paragraph. What would you want more?</P>
      <P>Lovely Spam! (Lovely Spam!) Lovely Spam! (Lovely Spam!) Lovely Spam! Spam, Spam, Spam, Spam!</P>
    </Section>

    {withHr ? <HR /> : null}
  </>
)

TitlesWithParagraphs.args = {
  withHr: false,
}
TitlesWithParagraphs.argTypes = {}
