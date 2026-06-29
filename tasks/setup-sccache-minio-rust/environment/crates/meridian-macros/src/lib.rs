use proc_macro::TokenStream;
use quote::quote;
use syn::{parse_macro_input, DeriveInput};

#[proc_macro_derive(MeridianLabel)]
pub fn derive_meridian_label(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input as DeriveInput);
    let name = input.ident;
    let expanded = quote! {
        impl #name {
            pub fn meridian_label(&self) -> &'static str {
                stringify!(#name)
            }
        }
    };
    expanded.into()
}
