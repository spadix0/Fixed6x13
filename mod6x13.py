# specific overrides for 6x13*
# these are applied to bitmaps loaded from original font before vectorization

def apply_bitmaps(font):
    font.family = 'Fixed 6x13'
    font.version = 1.0
    font.xheight = 6
    font.capheight = 9
    font.copyright = font.copyright.strip() + \
        '  This font is marked with CC0 1.0' + \
        ' (https://creativecommons.org/publicdomain/zero/1.0/)'
    glyphs = font.glyphs

    # swap 'ω' with 'ѡ': former looks too similar to 'w',
    # which is ok for latter, also ref '⍵⍹'
    font.set_glyph(glyphs['ω'].clone('ѡ'))
    # these should match
    glyphs['ѽ'].bitmap[5:] = glyphs['ѡ'].bitmap[5:]

    # shift (almost) all horizontal arrows up
    # to match box drawing lines '─' and operators '+'
    for ch in '←→↔↚↛↞↠↢↣↤↦↩↪↫↬↭↮↴↼↽⇀⇁⇋⇌⇍⇎⇏⇐⇒⇔⇚⇛⇠⇢⇤⇥⇦⇨⇰⇴⇷⇸⇺⇻⇽⇾⟵⟶⟷⟸⟹⟺⟻⟼⟽⟾⤆⤇':
        if ch in glyphs:
            glyphs[ch].shift(0, 1)

    if font.italic:
        # caps shift by 1px, but some asc/descenders by 2: 1.5:9 ≈ -9.5°
        # '[' and ']' shift by 2px: 2:11 ≈ -10.3°
        font.caret[0] = -10
    elif not font.bold:
        apply_regular(font)


def apply_regular(font):
    glyphs = font.glyphs

    # add missing 'ȷ' by cropping dot from 'j'
    ȷ = font.set_glyph(glyphs['j'].clone('ȷ'))
    ȷ.bitmap[3] = 0

    # trying out shorter middle stem for 'ω'
    ω = font.add_glyph_uniart('ω', '''
        ▕      ▏▁
         ▄▀ ▀▄
         █ ▄ █
         ▀▄▀▄▀
        ▔▔ ▔ ▔
    ''')

    # these should all match
    for ch in 'ώὠὡὢὣὤὥὦὧὼώᾠᾡᾢᾣᾤᾥᾦᾧῲῳῴῶῷ':
        glyphs[ch].bitmap[5:3+len(ω.bitmap)] = ω.bitmap[2:]

    # add just this new modifier (because it looks like superscript '!')
    font.add_glyph_uniart('ᵎ', '''
        ▕ ▄    ▏
        ▕ █
        ▕ ▄     ▁
        ▕
        ▕
        ▕
        ▔▔▔▔▔▔
    ''')

    # add some missing subscripts
    font.add_glyph_uniart('ₐ', '''
        ▕ ▄    ▏
          ▄█
        ▔▀▄█▔▔
    ''')

    font.add_glyph_uniart('ₑ', '''
        ▕ ▄    ▏
         █▄█
        ▔▀▄▄▔▔
    ''')

    font.add_glyph_uniart('ₒ', '''
        ▕▄▄▄   ▏
         █ █
        ▔█▄█▔▔
    ''')

    font.add_glyph_uniart('ₓ', '''
        ▕▄ ▄   ▏
         ▀▄▀
        ▔█ █▔▔
    ''')

    font.add_glyph_uniart('ₔ', '''
        ▕▄▄    ▏
         ▄▄█
        ▔▀▄▀▔▔
    ''')

    font.add_glyph_uniart('ₕ', '''
        ▕▄     ▏
         █▄
        ▔█ █▔▔
    ''')

    font.add_glyph_uniart('ₖ', '''
        ▕▄     ▏
         █▄▀
        ▔█ █▔▔
    ''')

    font.add_glyph_uniart('ₗ', '''
        ▕▄     ▏
         █
        ▔▀▄▔▔▔
    ''')

    # going to mess with tilde operator:  original is too low compared to
    # other operators and, IMO, '~' has nicer shape
    tildeop = glyphs['∼']
    tildeop.bitmap[3:] = glyphs['~'].bitmap[0:-3]

    # but then all of these should match:
    homothetic = font.set_glyph(tildeop.clone('∻'))
    for i in (3, 9):
        homothetic.bitmap[i] = 0b001000  # add dots above & below

    revtilde = font.set_glyph(tildeop.clone('∽'))
    revtilde.bitmap[5], revtilde.bitmap[7] = \
        revtilde.bitmap[7], revtilde.bitmap[5]  # flip

    notilde = font.set_glyph(tildeop.clone('≁'))
    for i in range(3, 9+1):
        notilde.bitmap[i] |= 0b001000  # add bar

    # all of these operators are too low (compare to '-')
    for ch in '≂≃≄≍≎≏≐≑≒≓≔≕≖≠≡≢≣≼≽⊂⊃⊄⊅⊏⊐⊓⊔⋍⋎⋏⋐⋑⋒⋓⋔⋘⋙':
        glyphs[ch].shift(0, 1)

    glyphs['⍨'].bitmap[6:] = tildeop.bitmap[5:-1]

    # add missing "white" version of '⦗⦘' (added in 5.1)
    font.add_glyph_uniart('⟬', '''
        ▕  ▄▄▀ ▏
        ▕ █ █   ▁
        ▕ █ █
        ▕ █ █
        ▕ ▀▄█
        ▔▔▔  ▀
    ''')

    font.add_glyph_uniart('⟭', '''
        ▕▀▄▄   ▏
        ▕ █ █   ▁
        ▕ █ █
        ▕ █ █
        ▕ █▄▀
        ▔▀  ▔▔
    ''')

    # add some missing arrows
    # FIXME many missing from Supplemental Arrows-B and Misc Symbols and Arrows
    font.add_glyph_uniart('⟳', '''
        ▕      ▏
         ▄▀▀▄█  ▁
         █ ▀▀▀
         █   ▄
         ▀▄▄▄▀
        ▔▔   ▔
    ''')

    font.add_glyph_uniart('⤒', '''
        ▕▄▄▄▄▄ ▏
          ▄█▄   ▁
         ▀ █ ▀
        ▕  █
        ▕  █
        ▔▔▔ ▔▔
    ''')

    font.add_glyph_uniart('⤓', '''
        ▕  ▄   ▏
        ▕  █    ▁
        ▕  █
         ▀▄█▄▀
         ▄▄█▄▄
        ▔
    ''')

    # add new operator
    font.add_glyph_uniart('⦂', '''
        ▕▄▀▀▄  ▏▁
        ▕▀▄▄▀
        ▕ ▄▄
        ▕█  █
        ▔ ▀▀ ▔
    ''')

    # more '∼' variants
    tildedot = font.set_glyph(tildeop.clone('⩪'))
    tildedot.bitmap[3] = 0b001000  # add dot above

    tilderise = font.set_glyph(tildeop.clone('⩫'))
    tilderise.bitmap[3] = 0b000100  # add right dot above
    tilderise.bitmap[9] = 0b010000  # add left dot below

    eqovertilde = font.set_glyph(
        glyphs['≂']
            .clone('⩳')
            .shift(0, -1) # back down
    )
    eqovertilde.bitmap[3] = eqovertilde.bitmap[5]  # add extra bar

    # add new "blackboard bold" characters.
    # since space is limited, we'll try out doubling just *one* side stroke
    # (some would normally be both sides) with *no* extra gap between doubled
    # strokes.  also replace the few original BMP glyphs for consistency
    font.add_glyph_uniart('𝔸', '''
        ▕  ▄   ▏
         ▄▀ █▄  ▁
         █  ██
         █▀▀██
         █  ██
        ▔  ▔▔
    ''')

    font.add_glyph_uniart('𝔹', '''
        ▕▄▄▄▄  ▏
         ██  █  ▁
         ██▄▄█
         ██  █
         ██▄▄▀
        ▔    ▔
    ''')

    font.add_glyph_uniart('ℂ', '''
        ▕ ▄▄▄  ▏	# replace, for consistency
         ██  ▀  ▁
         ██
         ██
         ▀█▄▄▀
        ▔▔   ▔
    ''')

    font.add_glyph_uniart('𝔻', '''
        ▕▄▄▄▄  ▏
         ██  █  ▁
         ██  █
         ██  █
         ██▄▄▀
        ▔    ▔
    ''')

    font.add_glyph_uniart('𝔼', '''
        ▕▄▄▄▄▄ ▏
         ██     ▁
         ██▄▄
         ██
         ██▄▄▄
        ▔
    ''')

    font.add_glyph_uniart('𝔽', '''
        ▕▄▄▄▄▄ ▏
         ██     ▁
         ██▄▄
         ██
         ██
        ▔  ▔▔▔
    ''')

    font.add_glyph_uniart('𝔾', '''
        ▕ ▄▄▄  ▏
         ██  ▀  ▁
         ██
         ██ ▀█
         ▀█▄▄▀
        ▔▔   ▔
    ''')

    font.add_glyph_uniart('ℍ', '''
        ▕▄▄  ▄ ▏	# replace, for consistency
         ██  █  ▁
         ██▄▄█
         ██  █
         ██  █
        ▔  ▔▔
    ''')

    font.add_glyph_uniart('𝕀', '''
        ▕ ▄▄▄▄ ▏
        ▕  ██   ▁
        ▕  ██
        ▕  ██
        ▕ ▄██▄
        ▔▔    ▔
    ''')

    font.add_glyph_uniart('𝕁', '''
        ▕  ▄▄▄▄▏
        ▕   ██  ▁
        ▕   ██
        ▕   ██
         ▀▄▄█▀
        ▔▔   ▔
    ''')

    font.add_glyph_uniart('𝕂', '''
        ▕▄▄  ▄ ▏
         ██ ▄▀  ▁
         ██▄▀
         ██ █
         ██  █
        ▔  ▔▔
    ''')

    font.add_glyph_uniart('𝕃', '''
        ▕▄▄    ▏
         ██     ▁
         ██
         ██
         ██▄▄▄
        ▔
    ''')

    font.add_glyph_uniart('𝕄', '''
        ▕▄▄   ▄▏
         ██▀▄▀█ ▁
         ██ ▀ █
         ██   █
         ██   █
        ▔  ▔▔▔
    ''')

    font.add_glyph_uniart('ℕ', '''
        ▕▄   ▄ ▏	# replace, for consistency
         ██  █  ▁
         ███ █
         ██ ██
         ██  █
        ▔  ▔▔
    ''')

    font.add_glyph_uniart('𝕆', '''
        ▕ ▄▄▄  ▏
         ██  █  ▁
         ██  █
         ██  █
         ▀█▄▄▀
        ▔▔   ▔
    ''')

    font.add_glyph_uniart('ℙ', '''
        ▕▄▄▄▄  ▏	# replace, for consistency
         ██  █  ▁
         ██▄▄▀
         ██
         ██
        ▔  ▔▔▔
    ''')

    font.add_glyph_uniart('ℚ', '''
        ▕ ▄▄▄  ▏	# replace, for consistency
         ██  █  ▁
         ██  █
         ██  █
         ▀█▄█▀
        ▔▔   ▀
    ''')

    font.add_glyph_uniart('ℝ', '''
        ▕▄▄▄▄  ▏	# replace, for consistency
         ██  █  ▁
         ██▄▄▀
         ██▀▄
         ██  █
        ▔  ▔▔
    ''')

    font.add_glyph_uniart('𝕊', '''
        ▕ ▄▄▄  ▏
         █▄  ▀  ▁
         ▀██▄
           ▀██
         ▀▄▄▄▀
        ▔▔   ▔
    ''')

    font.add_glyph_uniart('𝕋', '''
        ▕▄▄▄▄▄▄▏
        ▕  ██   ▁
        ▕  ██
        ▕  ██
        ▕  ██
        ▔▔▔  ▔
    ''')

    font.add_glyph_uniart('𝕌', '''
        ▕▄▄  ▄ ▏
         ██  █  ▁
         ██  █
         ██  █
         ▀█▄▄▀
        ▔▔   ▔
    ''')

    font.add_glyph_uniart('𝕍', '''
        ▕▄▄  ▄ ▏
         ██  █  ▁
         ██ ▄▀
         ▀█▄█
        ▕ ▀█
        ▔▔▔ ▔▔
    ''')

    font.add_glyph_uniart('𝕎', '''
        ▕▄▄   ▄▏
         ██   █ ▁
         ██   █
         ██ █ █
         ▀█▄▀▄▀
        ▔▔  ▔
    ''')

    font.add_glyph_uniart('𝕏', '''
        ▕▄▄  ▄ ▏
         ██ ▄▀  ▁
        ▕ ██▄
        ▕ ▄▀█▄
         █  ██
        ▔ ▔▔
    ''')

    font.add_glyph_uniart('𝕐', '''
        ▕▄▄   ▄▏
         ▀█▄ ▄▀ ▁
        ▕ ▀█▄▀
        ▕  ██
        ▕  ██
        ▔▔▔  ▔
    ''')

    font.add_glyph_uniart('ℤ', '''
        ▕▄▄▄▄▄ ▏	# replace, for consistency
        ▕  ▄█▀  ▁
        ▕ ▄██
        ▕ ██
         ██▄▄▄
        ▔
    ''')

    font.add_glyph_uniart('𝟘', '''
        ▕  ▄   ▏
         ▄█ ▀▄  ▁
         ██  █
         ██  █
        ▕ ▀▄▀
        ▔▔▔ ▔▔
    ''')

    font.add_glyph_uniart('𝟙', '''
        ▕  ▄▄  ▏
        ▕ ▀██   ▁
        ▕  ██
        ▕  ██
        ▕ ▄██▄
        ▔▔
    ''')

    font.add_glyph_uniart('𝟚', '''
        ▕ ▄▄▄  ▏
         █   █  ▁
        ▕  ▄██
         ▄██▀
         ██▄▄▄
        ▔
    ''')

    font.add_glyph_uniart('𝟛', '''
        ▕▄▄▄▄▄ ▏
        ▕   █▀  ▁
        ▕ ▄█▄
        ▕   ██
         ▀▄▄█▀
        ▔▔   ▔
    ''')

    font.add_glyph_uniart('𝟜', '''
        ▕    ▄ ▏
        ▕  ▄██  ▁
        ▕ █ ██
         █▄▄██▄
        ▕   ██
        ▔▔▔▔
    ''')

    font.add_glyph_uniart('𝟝', '''
        ▕▄▄▄▄▄ ▏
         ██     ▁
         ██▀█▄
        ▕   ██
         ▀▄▄█▀
        ▔▔   ▔
    ''')

    font.add_glyph_uniart('𝟞', '''
        ▕ ▄▄▄  ▏
         ██  ▀  ▁
         ██▄▄
         ██  █
         ▀█▄▄▀
        ▔▔   ▔
    ''')

    font.add_glyph_uniart('𝟟', '''
        ▕▄▄▄▄▄ ▏
            ██  ▁
           ██▀
          ▄█▀
          ██
        ▔▔  ▔▔
    ''')

    font.add_glyph_uniart('𝟠', '''
        ▕ ▄▄▄  ▏
         ██  █  ▁
         ▀█▄▄▀
         ██  █
         ▀█▄▄▀
        ▔▔   ▔
    ''')

    font.add_glyph_uniart('𝟡', '''
        ▕ ▄▄▄  ▏
         █  ██  ▁
         ▀▄▄██
            ██
        ▕▀▄▄█▀
        ▔▔   ▔
    ''')
